"""Remember the Google permission on THIS computer, so the app can stay connected between visits ("stay connected").

What is saved: Google's refresh token (a permission slip that can only read your YouTube videos) and the client ID it belongs to.
What is never saved: your videos, titles, view counts, passwords, or the short-lived access token.

Where: a file in your own user folder (``~/.signal_studio/google_connection.json``), outside the project and outside git.  On
macOS and Linux the file is readable by you only; on Windows the user folder is already private to your account.  Set
``SIGNAL_STUDIO_CONNECTION_FILE`` to use another place (the tests do, so they never touch the real file).

The feature exists only for a run on your own computer: ``stay_connected_allowed`` needs the setting ``GOOGLE_STAY_CONNECTED=1``
AND a visitor on this same computer.  The shared website never has either, so a visitor there can never see another's channel.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Mapping

ENV_PATH_NAME = "SIGNAL_STUDIO_CONNECTION_FILE"
ENV_SWITCH = "GOOGLE_STAY_CONNECTED"
LOCAL_ADDRESSES = {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"}
_TRUE = {"1", "true", "yes", "on"}


def store_path(environ: Mapping[str, str] | None = None) -> Path:
    environ = os.environ if environ is None else environ
    custom = (environ.get(ENV_PATH_NAME) or "").strip()
    return Path(custom) if custom else Path.home() / ".signal_studio" / "google_connection.json"


def switched_on(environ: Mapping[str, str] | None = None) -> bool:
    environ = os.environ if environ is None else environ
    return (environ.get(ENV_SWITCH) or "").strip().lower() in _TRUE


def is_this_computer(address: object) -> bool:
    """True only for a visitor connecting from this same computer (unknown or remote addresses are refused)."""
    return isinstance(address, str) and address.strip().lower() in LOCAL_ADDRESSES


def stay_connected_allowed(address: object, environ: Mapping[str, str] | None = None) -> bool:
    return switched_on(environ) and is_this_computer(address)


def save(refresh_token: str, client_id: str, path: Path | None = None) -> Path:
    """Write the permission file atomically, readable by this user only (where the system supports it)."""
    path = path or store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    payload = {"version": 1, "client_id": client_id, "refresh_token": refresh_token, "saved_at": int(time.time())}
    temporary = path.with_name(path.name + ".tmp")
    # create with owner-only permissions from the start, so the token is never readable by others even for a moment
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load(client_id: str, path: Path | None = None) -> str | None:
    """The saved refresh token, or None when there is none, the file is damaged, or it belongs to another Google client."""
    path = path or store_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("client_id") != client_id:
        return None
    token = data.get("refresh_token")
    return token if isinstance(token, str) and token else None


def exists(path: Path | None = None) -> bool:
    return (path or store_path()).is_file()


def forget(path: Path | None = None) -> bool:
    """Delete the permission file. True if there was one."""
    path = path or store_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
