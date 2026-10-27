"""Google sign-in (OAuth 2.0 authorization-code flow with PKCE) so a creator can connect their own YouTube channel.

Design, in plain words:
* Only the read-only YouTube scope is requested.  By default ``access_type=online``: Google gives a short-lived access token
  and no refresh token, so nothing long-lived exists.
* Optional "stay connected" (only for a local run, see ``connection_store``): ``access_type=offline`` also returns a refresh
  token, which the app keeps in a private file on that computer so the next visit needs no new sign-in.  It can be cancelled
  at any time (``revoke_grant``).
* PKCE (S256) and a random single-use ``state`` protect the redirect.  Streamlit loses its session when the browser goes
  to Google and comes back, so pending logins are kept in a small in-memory store, keyed by ``state``.  There is no time limit on finishing the sign-in
  (take as long as you like on Google's screen); an entry is removed when it is used, and only the oldest are dropped if more
  than ``MAX_PENDING`` logins are waiting at once.
* The access token lives only in the caller's session.  It is never logged, never put in a URL we build, and the class
  that holds it hides it from ``repr``.
* Settings come from environment variables (see ``.env.example``); no credential is ever in the code or the repository.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping
from urllib.parse import urlencode

import requests

SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
PENDING_TTL_S: float | None = None  # no time limit on finishing the sign-in; pass a number of seconds to PendingLogins to add one
MAX_PENDING = 200
HTTP_TIMEOUT_S = 15
DEFAULT_REDIRECT_URI = "http://localhost:8501/"

_FRIENDLY = {
    "access_denied": "You chose not to give access, so nothing was connected.",
    "invalid_grant": "Google no longer accepts that sign-in (it was already used, or Google ended it). Please start the connection again.",
    "invalid_client": "Google does not recognise this app's client settings (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).",
    "redirect_uri_mismatch": "The redirect address does not match the one registered in Google Cloud (GOOGLE_REDIRECT_URI).",
}


class OAuthError(Exception):
    """A sign-in problem, worded for the person using the app (never contains a code, token or secret)."""


class SavedConnectionEnded(OAuthError):
    """Google no longer accepts the saved permission (cancelled in the Google account, or ended by Google): connect again."""


@dataclass(frozen=True)
class OAuthConfig:
    client_id: str
    client_secret: str | None = field(default=None, repr=False)
    redirect_uri: str = DEFAULT_REDIRECT_URI


@dataclass(frozen=True)
class TokenSet:
    access_token: str = field(repr=False)  # repr=False: a token must never end up in a log line by accident
    expires_at: float
    refresh_token: str | None = field(default=None, repr=False)  # only present when the sign-in asked for offline access

    def expired(self, now: float | None = None) -> bool:
        return (time.time() if now is None else now) >= self.expires_at


def oauth_config_from_env(env: Mapping[str, str] | None = None) -> OAuthConfig | None:
    """The Google client settings, or None when this server has not been set up for Google sign-in."""
    env = os.environ if env is None else env
    client_id = (env.get("GOOGLE_CLIENT_ID") or "").strip()
    if not client_id:
        return None
    return OAuthConfig(
        client_id=client_id,
        client_secret=(env.get("GOOGLE_CLIENT_SECRET") or "").strip() or None,
        redirect_uri=(env.get("GOOGLE_REDIRECT_URI") or "").strip() or DEFAULT_REDIRECT_URI,
    )


class PendingLogins:
    """In-memory, thread-safe, single-use store of ``state -> code_verifier``.  Entries never time out unless ``ttl_s`` is given."""

    def __init__(self, ttl_s: float | None = PENDING_TTL_S, clock: Callable[[], float] = time.time) -> None:
        self._ttl = ttl_s
        self._clock = clock
        self._items: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def _purge(self) -> None:
        if self._ttl is None:
            return
        now = self._clock()
        for state in [s for s, (_, created) in self._items.items() if now - created > self._ttl]:
            del self._items[state]

    def put(self, state: str, verifier: str) -> None:
        with self._lock:
            self._purge()
            while len(self._items) >= MAX_PENDING:  # drop the oldest: a flood of logins cannot grow memory without bound
                del self._items[min(self._items, key=lambda s: self._items[s][1])]
            self._items[state] = (verifier, self._clock())

    def pop(self, state: str) -> str | None:
        """The verifier for ``state`` (removing it, so a state can be used once), or None if unknown (never started, already used, or the app restarted)."""
        with self._lock:
            self._purge()
            entry = self._items.pop(state, None)
        return entry[0] if entry else None

    def __len__(self) -> int:
        with self._lock:
            self._purge()
            return len(self._items)


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def begin_login(config: OAuthConfig, pending: PendingLogins, *, offline: bool = False) -> str:
    """The Google address to send the creator to; remembers the PKCE verifier under a fresh ``state``.

    ``offline=True`` also asks for a refresh token ("stay connected"); Google then always shows its permission screen."""
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    pending.put(state, verifier)
    query = urlencode({
        "client_id": config.client_id, "redirect_uri": config.redirect_uri, "response_type": "code", "scope": SCOPE,
        "state": state, "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "access_type": "offline" if offline else "online", "prompt": "select_account consent" if offline else "select_account",
    })
    return f"{AUTH_URL}?{query}"


def finish_login(
    config: OAuthConfig,
    pending: PendingLogins,
    params: Mapping[str, str],
    *,
    post: Callable[..., requests.Response] | None = None,
    now: float | None = None,
) -> TokenSet:
    """Exchange the ``code`` Google sent back for an access token (checks ``state``, uses the PKCE verifier)."""
    post = post or requests.post
    if params.get("error"):
        raise OAuthError(_FRIENDLY.get(params["error"], "Google did not complete the sign-in."))
    code, state = params.get("code"), params.get("state")
    if not code or not state:
        raise OAuthError("The sign-in response from Google was incomplete.")
    verifier = pending.pop(state)
    if verifier is None:
        raise OAuthError("This sign-in was already used, or the app was restarted after you started it. Please start the connection again.")
    data = {
        "client_id": config.client_id, "code": code, "code_verifier": verifier,
        "grant_type": "authorization_code", "redirect_uri": config.redirect_uri,
    }
    if config.client_secret:
        data["client_secret"] = config.client_secret
    try:
        response = post(TOKEN_URL, data=data, timeout=HTTP_TIMEOUT_S)
    except requests.RequestException as error:
        raise OAuthError("Could not reach Google to finish the sign-in. Check the internet connection and try again.") from error
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code != 200 or "access_token" not in body:
        raise OAuthError(_FRIENDLY.get(str(body.get("error", "")), "Google rejected the sign-in. Please try again."))
    granted = str(body.get("scope", SCOPE)).split()
    if SCOPE not in granted:
        raise OAuthError("Access to your YouTube videos was not granted, so nothing was connected.")
    lifetime = float(body.get("expires_in", 3600))
    refresh = str(body["refresh_token"]) if body.get("refresh_token") else None
    return TokenSet(access_token=str(body["access_token"]), expires_at=(time.time() if now is None else now) + max(lifetime - 60, 0),
                    refresh_token=refresh)


def refresh_access_token(
    config: OAuthConfig,
    refresh_token: str,
    *,
    post: Callable[..., requests.Response] | None = None,
    now: float | None = None,
) -> TokenSet:
    """A fresh short-lived access token from a saved refresh token (no sign-in screen).

    Raises ``SavedConnectionEnded`` when Google says the permission is gone, so the caller can forget the saved file; any other
    problem (no internet, a Google hiccup) is a plain ``OAuthError`` and the saved permission is kept."""
    post = post or requests.post
    data = {"client_id": config.client_id, "refresh_token": refresh_token, "grant_type": "refresh_token"}
    if config.client_secret:
        data["client_secret"] = config.client_secret
    try:
        response = post(TOKEN_URL, data=data, timeout=HTTP_TIMEOUT_S)
    except requests.RequestException as error:
        raise OAuthError("Could not reach Google to renew your saved connection. Check the internet connection and try again.") from error
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code != 200 or "access_token" not in body:
        if str(body.get("error", "")) in {"invalid_grant", "invalid_client", "unauthorized_client"}:
            raise SavedConnectionEnded("Google no longer accepts your saved connection (it was cancelled, or Google ended it). "
                                       "Please connect again.")
        raise OAuthError("Google could not renew your saved connection just now. Please try again in a moment.")
    lifetime = float(body.get("expires_in", 3600))
    return TokenSet(access_token=str(body["access_token"]), expires_at=(time.time() if now is None else now) + max(lifetime - 60, 0),
                    refresh_token=refresh_token)


def revoke_grant(refresh_token: str, *, post: Callable[..., requests.Response] | None = None) -> bool:
    """Cancel the whole permission at Google (the saved refresh token and every access token made from it).

    Returns True when Google confirmed.  Failures are reported, not hidden, because the person asked to disconnect."""
    try:
        reply = (post or requests.post)(REVOKE_URL, data={"token": refresh_token}, timeout=HTTP_TIMEOUT_S)
    except requests.RequestException:
        return False
    return getattr(reply, "status_code", 0) == 200


def revoke(token: TokenSet, *, post: Callable[..., requests.Response] | None = None) -> None:
    """Ask Google to cancel the token (best effort: failures are ignored, the token is short-lived anyway)."""
    try:
        (post or requests.post)(REVOKE_URL, data={"token": token.access_token}, timeout=HTTP_TIMEOUT_S)
    except requests.RequestException:
        pass
