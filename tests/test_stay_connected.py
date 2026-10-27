"""'Keep me connected on this computer', driven through the real Streamlit app.

Google itself is SIMULATED here (consent cannot be triggered by a test): the tests replace only the calls that would reach Google
(token exchange, refresh, cancel, the YouTube read).  The channel that "Google" returns is a real channel from the data, and the
saved-permission file is the real store, pointed at a temporary file so the owner's real connection is never touched.
"""

from __future__ import annotations

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import connection_store, youtube_api, youtube_oauth
from tests.real_data import real_channel, requires_data
from tests.test_app import APP_PATH, _button

pytestmark = requires_data
CLIENT = "client-123.apps.googleusercontent.com"
REFRESH = "1//" + "refresh" + "-token-that-must-never-leak"


@pytest.fixture()
def world(monkeypatch, tmp_path):
    """A computer with Google 'switched on' for this app, a private temporary permission file, and a recording of what reached Google."""
    saved_file = tmp_path / "google_connection.json"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT)
    monkeypatch.setenv("GOOGLE_STAY_CONNECTED", "1")
    monkeypatch.setenv(connection_store.ENV_PATH_NAME, str(saved_file))
    monkeypatch.setattr(type(st.context), "ip_address", property(lambda self: "127.0.0.1"))  # the visitor is on this computer
    history = real_channel()
    log = {"revoked": [], "revoked_grants": [], "refreshed": [], "fetched": 0}
    token = youtube_oauth.TokenSet("ya29.ACCESS", float("inf"), refresh_token=REFRESH)

    def fetch(tok, *args, **kwargs):
        log["fetched"] += 1
        return history, {"title": "A real channel"}

    monkeypatch.setattr(youtube_oauth, "finish_login", lambda config, pending, params, **k: token)
    monkeypatch.setattr(youtube_oauth, "refresh_access_token", lambda config, saved, **k: (log["refreshed"].append(saved), token)[1])
    monkeypatch.setattr(youtube_oauth, "revoke", lambda tok, **k: log["revoked"].append(tok))
    monkeypatch.setattr(youtube_oauth, "revoke_grant", lambda saved, **k: (log["revoked_grants"].append(saved), True)[1])
    monkeypatch.setattr(youtube_api, "fetch_channel_history", fetch)
    return {"file": saved_file, "history": history, "log": log, "token": token}


def _new_session() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=180)


def _returning_from_google() -> AppTest:
    app = _new_session()
    app.query_params["code"], app.query_params["state"] = "the-code", "the-state"
    return app.run()


def _texts(app: AppTest) -> str:
    return " ".join([m.value for m in app.success] + [m.value for m in app.error] + [m.value for m in app.info])


def test_choosing_to_stay_connected_keeps_the_permission_and_does_not_cancel_it(world):
    app = _returning_from_google()
    assert not app.exception
    assert connection_store.load(CLIENT, world["file"]) == REFRESH
    assert world["log"]["revoked"] == [], "the access must stay, otherwise the saved permission would be dead"
    assert len(app.session_state["channel"].videos) == len(world["history"].videos)
    assert "kept on this computer" in _texts(app)
    assert REFRESH not in str(app.session_state["channel"]) and "ya29.ACCESS" not in _texts(app)


def test_without_a_saved_connection_nothing_is_loaded_and_nothing_reaches_google(world):
    app = _new_session().run()
    assert not app.exception and "channel" not in app.session_state
    assert world["log"]["refreshed"] == [] and world["log"]["fetched"] == 0


def test_a_new_session_loads_the_channel_by_itself_from_the_saved_connection(world):
    connection_store.save(REFRESH, CLIENT, world["file"])
    app = _new_session().run()
    assert not app.exception
    assert world["log"]["refreshed"] == [REFRESH]
    assert len(app.session_state["channel"].videos) == len(world["history"].videos)
    assert "Welcome back, A real channel" in _texts(app)
    assert world["log"]["revoked"] == [] and world["file"].exists(), "reading again must not cancel the permission"
    labels = {metric.label for metric in app.metric}
    assert "Videos loaded" in labels


def test_remove_my_data_forgets_this_session_but_not_the_connection_and_does_not_reload(world):
    connection_store.save(REFRESH, CLIENT, world["file"])
    app = _new_session().run()
    assert "channel" in app.session_state
    _button(app, "Remove my data").click().run()
    assert not app.exception
    assert "channel" not in app.session_state, "removing the data must really forget it, not reload it on the next rerun"
    assert world["file"].exists(), "the saved connection is only removed by Disconnect"
    assert world["log"]["refreshed"] == [REFRESH], "no second read happened"


def test_disconnect_cancels_the_permission_at_google_deletes_the_file_and_forgets_the_channel(world):
    connection_store.save(REFRESH, CLIENT, world["file"])
    app = _new_session().run()
    app.button(key="google_disconnect").click().run()
    assert not app.exception
    assert world["log"]["revoked_grants"] == [REFRESH]
    assert not world["file"].exists() and "channel" not in app.session_state
    assert "Disconnected" in _texts(app)
    assert not [b for b in app.button if b.key == "google_disconnect"], "nothing left to disconnect"


def test_a_connection_google_no_longer_accepts_is_deleted_with_a_plain_message(world, monkeypatch):
    connection_store.save(REFRESH, CLIENT, world["file"])

    def ended(config, saved, **kwargs):
        raise youtube_oauth.SavedConnectionEnded("Google no longer accepts your saved connection. Please connect again.")

    monkeypatch.setattr(youtube_oauth, "refresh_access_token", ended)
    app = _new_session().run()
    assert not app.exception and "channel" not in app.session_state
    assert not world["file"].exists(), "a dead permission must not be tried at every start"
    assert "no longer accepts" in _texts(app)


def test_a_temporary_problem_keeps_the_saved_connection(world, monkeypatch):
    connection_store.save(REFRESH, CLIENT, world["file"])

    def offline(config, saved, **kwargs):
        raise youtube_oauth.OAuthError("Could not reach Google to renew your saved connection.")

    monkeypatch.setattr(youtube_oauth, "refresh_access_token", offline)
    app = _new_session().run()
    assert not app.exception and "channel" not in app.session_state
    assert world["file"].exists(), "no internet for a minute must not cost the person their connection"
    assert "kept" in _texts(app)


def test_the_login_asks_for_offline_access_only_when_the_box_is_ticked(world):
    app = _new_session().run()
    assert app.checkbox(key="stay_connected").value is True, "on the owner's own computer it is the default"
    app.button(key="google_connect").click().run()
    assert "access_type=offline" in app.session_state["google_auth_url"]
    app = _new_session().run()
    app.checkbox(key="stay_connected").uncheck().run()
    app.button(key="google_connect").click().run()
    assert "access_type=online" in app.session_state["google_auth_url"] and "access_type=offline" not in app.session_state["google_auth_url"]


def test_a_visitor_from_the_network_never_gets_the_saved_connection(world, monkeypatch):
    """The shared-computer case: even with the file present and the setting on, a remote visitor sees nothing of it."""
    connection_store.save(REFRESH, CLIENT, world["file"])
    monkeypatch.setattr(type(st.context), "ip_address", property(lambda self: "203.0.113.5"))
    app = _new_session().run()
    assert not app.exception and "channel" not in app.session_state
    assert world["log"]["refreshed"] == [] and world["log"]["fetched"] == 0
    assert not [c for c in app.checkbox if c.key == "stay_connected"] and not [b for b in app.button if b.key == "google_disconnect"]
    app.button(key="google_connect").click().run()
    assert "access_type=online" in app.session_state["google_auth_url"]


def test_the_shared_website_has_the_feature_off_by_default(world, monkeypatch):
    monkeypatch.setenv("GOOGLE_STAY_CONNECTED", "")  # empty counts as set, so the owner's real .env cannot switch it back on
    connection_store.save(REFRESH, CLIENT, world["file"])
    app = _new_session().run()
    assert "channel" not in app.session_state and world["log"]["refreshed"] == []
    app = _returning_from_google()
    assert world["log"]["revoked"] == [world["token"]], "without the setting the access is cancelled right after reading, as before"
    assert connection_store.load(CLIENT, world["file"]) == REFRESH, "the stale file from before is untouched and never used"


def test_a_failed_read_after_signing_in_cancels_the_permission_it_just_got(world, monkeypatch):
    def broken(tok, *args, **kwargs):
        raise youtube_api.YouTubeAPIError("YouTube is having a problem right now.")

    monkeypatch.setattr(youtube_api, "fetch_channel_history", broken)
    app = _returning_from_google()
    assert not app.exception and "channel" not in app.session_state
    assert world["log"]["revoked"] == [world["token"]] and not world["file"].exists()
