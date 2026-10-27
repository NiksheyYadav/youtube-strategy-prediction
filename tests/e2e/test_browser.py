"""What a person sees and can do in the real app, in a real browser."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from tests.e2e.visitor import Visitor
from tests.real_data import CLEAN_PATH, requires_data
from tests.real_videos import REAL_VIDEOS

TABS = ["Forecast studio", "My channel", "Best time", "Title lab", "AI coach", "Similar videos", "Scenario lab", "YouTube timeline", "Model brief"]
VIDEO = REAL_VIDEOS[0]


def test_first_visit_is_an_empty_form_with_a_clear_next_step(visitor: Visitor):
    assert visitor.exceptions() == 0
    assert visitor.page.locator('textarea[aria-label="Video title"]').first.input_value() == ""
    text = visitor.text()
    assert "Start with your draft" in text
    assert "demo" not in text.lower() and "viva" not in text.lower()
    assert visitor.page.get_by_text("Deploy", exact=True).count() == 0, "no developer toolbar on a finished product"
    assert [name.strip() for name in visitor.page.get_by_role("tab").all_inner_texts()] == TABS


def test_a_written_draft_gets_a_forecast_with_honest_wording(visitor: Visitor):
    visitor.write_draft(VIDEO["title"], VIDEO["tags"], VIDEO["description"])
    assert visitor.exceptions() == 0
    metrics = visitor.metrics()
    assert metrics["Expected views"] and metrics["Expected engagement"]
    text = visitor.text()
    assert "80% interval" in text and "not as a promise" in text and "channels the model had never seen" in text
    assert not visitor.errors


def test_every_tab_works_after_a_draft_is_written(visitor: Visitor):
    visitor.write_draft(VIDEO["title"], VIDEO["tags"], VIDEO["description"])
    for name in TABS:
        visitor.tab(name)
        assert visitor.exceptions() == 0, f"error box on the {name} tab"
    assert not visitor.errors


@pytest.mark.parametrize("title", [
    '<img src=x onerror="window.__xss=1"><script>window.__xss=2</script>',
    "[click](javascript:window.__xss=3) **bold** `code` ![i](http://example.invalid/x.png)",
    "🔥" * 100,
    "‮evil‬ title with a right-to-left override",
])
def test_hostile_titles_are_shown_as_text_and_run_nothing(visitor: Visitor, title: str):
    visitor.write_draft(title)
    assert visitor.exceptions() == 0
    assert visitor.page.evaluate("() => window.__xss === undefined"), "text typed into the form was executed as a script"
    assert visitor.page.locator("img[src='x']").count() == 0


def test_a_title_in_hindi_is_forecast_and_the_weaker_accuracy_is_stated(visitor: Visitor):
    visitor.write_draft("भारत की सबसे बड़ी खबर आज सुबह")
    assert visitor.exceptions() == 0
    text = visitor.text()
    assert visitor.metrics()["Expected views"]
    assert "script other than the Latin alphabet" in text


def test_on_a_phone_the_sidebar_starts_closed_and_the_tabs_are_usable(phone_visitor: Visitor):
    page = phone_visitor.page
    assert not page.locator('[data-testid="stSidebar"][aria-expanded="true"]').count(), "an open sidebar would cover the whole page"
    phone_visitor.tab("Model brief")
    assert phone_visitor.exceptions() == 0
    assert "Validation at a glance" in phone_visitor.text()
    overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, f"the page scrolls sideways by {overflow}px on a phone"


def test_a_picture_renamed_to_csv_is_refused_politely(visitor: Visitor, tmp_path):
    bad = tmp_path / "photo.csv"
    bad.write_bytes(b"\x89PNG\r\n\x1a\n" + os.urandom(3000))
    visitor.upload(bad)
    assert visitor.exceptions() == 0
    assert "Videos loaded" not in visitor.metrics()
    assert visitor.page.locator('[data-testid="stAlert"]').count() >= 1


def test_the_strategy_brief_can_be_downloaded(visitor: Visitor):
    visitor.write_draft(VIDEO["title"], VIDEO["tags"], VIDEO["description"])
    with visitor.page.expect_download(timeout=60000) as download:
        visitor.page.get_by_role("button", name="Download strategy brief (.md)").click()
    brief = Path(download.value.path()).read_text(encoding="utf-8")
    assert "# Pre-publication strategy brief" in brief and "<script" not in brief.lower()


# --------------------------------------------------------------------------- #
# A creator's own data (a real channel's real videos from the dataset, written as a Studio-style file)
# --------------------------------------------------------------------------- #
def _real_channel_file(tmp_path: Path) -> tuple[Path, int]:
    data = pd.read_csv(CLEAN_PATH)
    counts = data["channel_title"].value_counts()
    name = counts[counts >= 25].index[0]
    rows = data[data["channel_title"] == name]
    frame = pd.DataFrame({"Video title": rows["title"], "Video publish time": rows["publish_time"], "Views": rows["views"],
                          "Likes": rows["likes"], "Comments": rows["comment_count"]})
    path = tmp_path / "Table data.csv"
    frame.to_csv(path, index=False)
    return path, len(frame)


@requires_data
def test_a_creators_file_personalises_the_forecast_and_can_be_removed(visitor: Visitor, tmp_path):
    path, count = _real_channel_file(tmp_path)
    visitor.upload(path)
    visitor.wait_for(lambda: "Videos loaded" in visitor.metrics())
    assert visitor.exceptions() == 0
    assert visitor.metrics()["Videos loaded"] == str(count)
    visitor.write_draft(VIDEO["title"], VIDEO["tags"], VIDEO["description"])
    metrics = visitor.metrics()
    assert metrics["Expected views for your channel"] and metrics["Your usual video"]
    assert metrics["This draft vs your usual"].endswith("%")

    visitor.page.get_by_role("button", name="Remove my data").first.click()
    visitor.wait_for(lambda: "Expected views for your channel" not in visitor.metrics())
    visitor.idle()  # the rest of the page (the My channel tab) is redrawn later in the same rerun
    assert "Videos loaded" not in visitor.metrics()


@requires_data
def test_one_visitors_channel_data_is_never_shown_to_another(visitor: Visitor, browser, app_url, tmp_path):
    path, _ = _real_channel_file(tmp_path)
    visitor.upload(path)
    visitor.wait_for(lambda: "Videos loaded" in visitor.metrics())
    visitor.write_draft(VIDEO["title"])
    visitor.wait_for(lambda: "Expected views for your channel" in visitor.metrics())

    other_context = browser.new_context(viewport={"width": 1366, "height": 900})
    try:
        other = Visitor(other_context.new_page(), app_url).open()
        other.write_draft(VIDEO["title"])
        assert "Expected views for your channel" not in other.metrics()
        assert "videos loaded" not in other.text().lower()
    finally:
        other_context.close()


@pytest.mark.skipif(not os.environ.get("SIGNAL_STUDIO_EXPORT"), reason="set SIGNAL_STUDIO_EXPORT to the path of your own YouTube Studio export (.csv or .zip) to run this")
def test_your_own_youtube_studio_export_loads(visitor: Visitor):
    visitor.upload(Path(os.environ["SIGNAL_STUDIO_EXPORT"]))
    assert visitor.exceptions() == 0
    assert int(visitor.metrics()["Videos loaded"]) > 0
    visitor.write_draft(VIDEO["title"], VIDEO["tags"], VIDEO["description"])
    assert visitor.exceptions() == 0
