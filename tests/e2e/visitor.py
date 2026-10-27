"""A person using the app in a real browser tab (shared by the browser tests)."""

from __future__ import annotations

import time
from pathlib import Path


class Visitor:
    """One person using the app in a real browser tab."""

    def __init__(self, page, url: str):
        self.page, self.url, self.errors = page, url, []
        page.on("pageerror", lambda error: self.errors.append(str(error)[:200]))

    def open(self) -> "Visitor":
        self.page.goto(self.url)
        self.page.wait_for_selector('[role="tablist"]', timeout=120000)
        self.idle()
        return self

    def idle(self, extra: float = 0.6) -> None:
        time.sleep(0.3)  # let a click start its rerun before asking whether the app is busy
        self.page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=180000)
        time.sleep(extra)

    def wait_for(self, condition, timeout: float = 40.0) -> None:
        """Wait until ``condition()`` is true (for example a result appearing or going away after a click)."""
        deadline = time.time() + timeout
        while not condition():
            if time.time() > deadline:
                raise AssertionError("the page did not reach the expected state in time")
            time.sleep(0.4)

    def tab(self, name: str) -> None:
        self.page.get_by_role("tab", name=name, exact=True).click()
        self.idle()

    def exceptions(self) -> int:
        return self.page.locator('[data-testid="stException"]').count()

    def text(self) -> str:
        return self.page.inner_text("body")

    def metrics(self) -> dict[str, str]:
        labels = self.page.locator('[data-testid="stMetricLabel"]').all_inner_texts()
        values = self.page.locator('[data-testid="stMetricValue"]').all_inner_texts()
        return dict(zip([label.strip() for label in labels], [value.strip() for value in values]))

    def write_draft(self, title: str, tags: str = "", description: str = "") -> None:
        self.tab("Forecast studio")
        field = self.page.locator('textarea[aria-label="Video title"]').first
        field.fill(title)
        field.press("Tab")
        self.page.locator('input[aria-label="Tags"]').first.fill(tags)
        self.page.locator('textarea[aria-label="Description"]').first.fill(description)
        self.page.get_by_role("button", name="Generate pre-publication forecast").click()
        self.idle(1.2)

    def upload(self, path: Path) -> None:
        self.tab("My channel")
        self.page.set_input_files('input[type="file"]', str(path))
        self.idle(1.5)
