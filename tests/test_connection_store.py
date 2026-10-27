"""The saved Google permission: where it lives, who may use it, and that nothing but the permission slip is ever written."""

from __future__ import annotations

import json
import os
import stat
import sys

import pytest

from src import connection_store as store

CLIENT = "client-123.apps.googleusercontent.com"
TOKEN = "1//" + "refresh" + "-token-that-must-stay-private"  # built from pieces so the repo's secret scanner stays strict


def test_save_then_load_round_trip_and_forget(tmp_path):
    path = tmp_path / "connection.json"
    assert store.load(CLIENT, path) is None and not store.exists(path)
    store.save(TOKEN, CLIENT, path)
    assert store.exists(path) and store.load(CLIENT, path) == TOKEN
    assert store.forget(path) is True and store.load(CLIENT, path) is None
    assert store.forget(path) is False, "forgetting twice is harmless"


def test_only_the_permission_slip_is_written(tmp_path):
    path = tmp_path / "connection.json"
    store.save(TOKEN, CLIENT, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "client_id", "refresh_token", "saved_at"}, "no videos, titles, view counts or access tokens"
    assert not list(tmp_path.glob("*.tmp")), "the temporary file of the atomic write is gone"


def test_a_permission_saved_for_another_google_client_is_ignored(tmp_path):
    path = tmp_path / "connection.json"
    store.save(TOKEN, CLIENT, path)
    assert store.load("another-client.apps.googleusercontent.com", path) is None


@pytest.mark.parametrize("content", ["", "not json", "[1, 2]", '{"client_id": "client-123.apps.googleusercontent.com"}',
                                     '{"client_id": "client-123.apps.googleusercontent.com", "refresh_token": ""}'])
def test_a_damaged_file_is_treated_as_no_connection(tmp_path, content):
    path = tmp_path / "connection.json"
    path.write_text(content, encoding="utf-8")
    assert store.load(CLIENT, path) is None


@pytest.mark.skipif(sys.platform == "win32", reason="Windows does not use Unix permission bits; the user folder is private to the account")
def test_the_file_is_readable_by_its_owner_only(tmp_path):
    path = tmp_path / "private" / "connection.json"
    store.save(TOKEN, CLIENT, path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700


def test_default_location_is_in_the_user_folder_not_in_the_project():
    path = store.store_path({})
    assert path.name == "google_connection.json" and ".signal_studio" in path.parts
    assert store.store_path({store.ENV_PATH_NAME: "C:/somewhere/else.json"}).name == "else.json"


@pytest.mark.parametrize("value, expected", [("1", True), ("true", True), ("YES", True), ("on", True), ("0", False), ("", False), ("no", False)])
def test_the_setting_must_be_switched_on_explicitly(value, expected):
    assert store.switched_on({store.ENV_SWITCH: value}) is expected
    assert store.switched_on({}) is False


@pytest.mark.parametrize("address, expected", [("127.0.0.1", True), ("::1", True), ("localhost", True), ("::ffff:127.0.0.1", True),
                                               ("192.168.1.20", False), ("203.0.113.5", False), ("", False), (None, False), (7, False)])
def test_only_a_visitor_on_this_computer_counts_as_local(address, expected):
    assert store.is_this_computer(address) is expected


def test_staying_connected_needs_both_the_setting_and_a_local_visitor():
    on = {store.ENV_SWITCH: "1"}
    assert store.stay_connected_allowed("127.0.0.1", on) is True
    assert store.stay_connected_allowed("203.0.113.5", on) is False, "a visitor from the network never gets it"
    assert store.stay_connected_allowed("127.0.0.1", {}) is False, "the shared website never switches it on"
    assert store.stay_connected_allowed(None, on) is False, "an unknown visitor is treated as remote"
