"""Real-browser tests: the real app is started as a separate process and driven in real Chrome (no stand-ins).

Run only these:   python -m pytest tests/e2e -v
Skip them:        python -m pytest -m "not browser"
They skip themselves, with a reason, when Playwright or Chrome/Edge is not installed.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tests.e2e.visitor import Visitor

ROOT = Path(__file__).resolve().parents[2]
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - depends on the machine
    sync_playwright = None


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/e2e" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.browser)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="session")
def app_url(tmp_path_factory):
    """The app, started exactly as a user would start it, on a free port that only this computer can reach.

    The saved-Google-permission file is pointed at an empty throw-away location, so these tests can never pick up (or touch) the
    owner's real "keep me connected" file."""
    port = _free_port()
    environment = {**os.environ, "SIGNAL_STUDIO_CONNECTION_FILE": str(tmp_path_factory.mktemp("connection") / "google_connection.json")}
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port), "--server.address", "127.0.0.1",
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(url + "/_stcore/health", timeout=2) as reply:
                    if reply.status == 200:
                        break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("the app did not start within 60 seconds")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def browser():
    if sync_playwright is None:
        pytest.skip("Playwright is not installed (pip install -r requirements-dev.txt)")
    with sync_playwright() as playwright:
        for channel in ("chrome", "msedge"):
            try:
                opened = playwright.chromium.launch(channel=channel, headless=True)
                break
            except Exception:  # that browser is not installed here
                continue
        else:
            pytest.skip("neither Chrome nor Edge is installed")
        yield opened
        opened.close()


@pytest.fixture()
def visitor(browser, app_url):
    context = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
    person = Visitor(context.new_page(), app_url).open()
    yield person
    context.close()


@pytest.fixture()
def phone_visitor(browser, app_url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    person = Visitor(context.new_page(), app_url).open()
    yield person
    context.close()
