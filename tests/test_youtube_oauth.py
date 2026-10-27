from urllib.parse import parse_qs, urlparse

import pytest
import requests

from src.youtube_oauth import (
    SCOPE,
    OAuthConfig,
    OAuthError,
    PendingLogins,
    TokenSet,
    begin_login,
    finish_login,
    oauth_config_from_env,
    revoke,
    _challenge,
)

SECRET = "GOCSPX-" + "fake" + "-value-that-must-never-leak"  # built from pieces so the repo's secret scanner stays strict
CONFIG = OAuthConfig("client-123.apps.googleusercontent.com", SECRET, "http://localhost:8501/")


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {}

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def _login(pending):
    url = begin_login(CONFIG, pending)
    query = {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}
    return url, query


def test_config_comes_from_the_environment_and_is_none_when_not_set_up():
    assert oauth_config_from_env({}) is None
    config = oauth_config_from_env({"GOOGLE_CLIENT_ID": " abc ", "GOOGLE_CLIENT_SECRET": SECRET})
    assert config.client_id == "abc" and config.redirect_uri == "http://localhost:8501/"
    assert SECRET not in repr(config), "the client secret must not appear in repr/logs"
    assert oauth_config_from_env({"GOOGLE_CLIENT_ID": "x", "GOOGLE_REDIRECT_URI": "https://example.test/"}).redirect_uri == "https://example.test/"
    assert oauth_config_from_env({"GOOGLE_CLIENT_ID": "x"}).client_secret is None


def test_login_url_uses_pkce_state_read_only_scope_and_no_refresh_token():
    pending = PendingLogins()
    url, query = _login(pending)
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert query["scope"] == SCOPE == "https://www.googleapis.com/auth/youtube.readonly"
    assert query["response_type"] == "code" and query["access_type"] == "online"
    assert query["code_challenge_method"] == "S256" and query["client_id"] == CONFIG.client_id
    assert len(query["state"]) >= 40
    assert SECRET not in url and "client_secret" not in url
    verifier = pending.pop(query["state"])
    assert verifier and len(verifier) >= 43
    assert query["code_challenge"] == _challenge(verifier), "the challenge must be the S256 hash of the stored verifier"


def test_every_login_gets_a_new_state():
    pending = PendingLogins()
    assert _login(pending)[1]["state"] != _login(pending)[1]["state"]


def test_successful_exchange_sends_the_verifier_and_returns_a_token_that_hides_itself():
    pending = PendingLogins()
    _, query = _login(pending)
    sent = {}

    def post(url, data=None, timeout=None):
        sent.update(url=url, data=data, timeout=timeout)
        return FakeResponse(200, {"access_token": "ya29.TOKEN", "expires_in": 3600, "scope": SCOPE})

    token = finish_login(CONFIG, pending, {"code": "AUTHCODE", "state": query["state"]}, post=post, now=1000.0)
    assert sent["url"] == "https://oauth2.googleapis.com/token" and sent["timeout"] > 0
    assert sent["data"]["grant_type"] == "authorization_code" and sent["data"]["code"] == "AUTHCODE"
    assert _challenge(sent["data"]["code_verifier"]) == query["code_challenge"]
    assert token.access_token == "ya29.TOKEN" and token.expires_at == pytest.approx(1000.0 + 3540)
    assert not token.expired(now=1000.0) and token.expired(now=1000.0 + 3600)
    assert "ya29.TOKEN" not in repr(token) and "ya29.TOKEN" not in str(token)


def test_a_state_can_only_be_used_once_and_unknown_states_are_rejected():
    pending = PendingLogins()
    _, query = _login(pending)

    def post(*args, **kwargs):
        return FakeResponse(200, {"access_token": "t", "expires_in": 3600, "scope": SCOPE})

    finish_login(CONFIG, pending, {"code": "c", "state": query["state"]}, post=post)
    with pytest.raises(OAuthError, match="expired or was already used"):
        finish_login(CONFIG, pending, {"code": "c", "state": query["state"]}, post=post)  # replay
    with pytest.raises(OAuthError, match="expired or was already used"):
        finish_login(CONFIG, pending, {"code": "c", "state": "forged-state"}, post=post)  # CSRF attempt


def test_pending_logins_expire_and_are_bounded():
    clock = [0.0]
    pending = PendingLogins(ttl_s=600, clock=lambda: clock[0])
    pending.put("old", "verifier")
    clock[0] = 601
    assert pending.pop("old") is None
    for number in range(500):
        pending.put(f"s{number}", "v")
    assert len(pending) <= 200


@pytest.mark.parametrize("params, message", [
    ({"error": "access_denied"}, "chose not to give access"),
    ({"error": "something_else"}, "did not complete"),
    ({"state": "x"}, "incomplete"),
    ({"code": "x"}, "incomplete"),
])
def test_google_errors_and_incomplete_responses_have_friendly_messages(params, message):
    with pytest.raises(OAuthError, match=message):
        finish_login(CONFIG, PendingLogins(), params, post=lambda *a, **k: FakeResponse())


def test_failures_never_leak_the_code_the_secret_or_the_token():
    pending = PendingLogins()
    cases = [
        FakeResponse(400, {"error": "invalid_grant", "error_description": "Bad code SECRETCODE"}),
        FakeResponse(401, {"error": "invalid_client"}),
        FakeResponse(200, {"access_token": "ya29.LEAK", "scope": "https://www.googleapis.com/auth/userinfo.email"}),
        FakeResponse(500, None),
    ]
    for response in cases:
        _, query = _login(pending)
        with pytest.raises(OAuthError) as caught:
            finish_login(CONFIG, pending, {"code": "SECRETCODE", "state": query["state"]}, post=lambda *a, _r=response, **k: _r)
        text = str(caught.value)
        assert "SECRETCODE" not in text and SECRET not in text and "ya29" not in text


def test_network_failure_is_reported_in_plain_words():
    pending = PendingLogins()
    _, query = _login(pending)

    def broken(*args, **kwargs):
        raise requests.ConnectionError("boom with SECRETCODE")

    with pytest.raises(OAuthError, match="Could not reach Google") as caught:
        finish_login(CONFIG, pending, {"code": "SECRETCODE", "state": query["state"]}, post=broken)
    assert "SECRETCODE" not in str(caught.value)


def test_revoke_posts_the_token_and_ignores_network_errors():
    sent = {}
    revoke(TokenSet("tok", 1.0), post=lambda url, data=None, timeout=None: sent.update(url=url, data=data))
    assert sent["url"] == "https://oauth2.googleapis.com/revoke" and sent["data"] == {"token": "tok"}

    def broken(*args, **kwargs):
        raise requests.Timeout()

    revoke(TokenSet("tok", 1.0), post=broken)  # must not raise
