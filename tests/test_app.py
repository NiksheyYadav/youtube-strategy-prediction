"""End-to-end smoke tests: the real Streamlit script is executed headlessly."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture()
def app():
    return AppTest.from_file(str(APP_PATH), default_timeout=180).run()


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_app_boots_with_every_tab_and_no_exception(app):
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Forecast studio", "Best time", "Title lab", "Similar videos", "Scenario lab", "Model brief",
    ]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expected views"] and metrics["Expected engagement"]
    assert "Best slot #1" in metrics


def test_every_example_draft_produces_a_forecast(app):
    for name in ("Music video", "Tech review", "Movie trailer", "Education tutorial"):
        app.selectbox(key="example_choice").select(name).run()
        _button(app, "Load example").click().run()
        assert not app.exception, name
        assert any(metric.label == "Expected views" for metric in app.metric), name


def test_applying_a_suggestion_updates_the_form_and_reforecasts(app):
    before = (app.session_state["main_title"], app.session_state["main_description"], app.session_state["main_tags"])
    key = next(button.key for button in app.button if button.key and button.key.startswith("apply_"))
    app.button(key=key).click().run()
    after = (app.session_state["main_title"], app.session_state["main_description"], app.session_state["main_tags"])
    assert after != before
    assert not app.exception


def test_best_slot_button_moves_the_planned_publish_time(app):
    app.button(key="slot_0").click().run()
    assert not app.exception
    assert app.session_state["main_day"] in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}


def test_blank_title_is_explained_not_crashed(app):
    app.text_area(key="main_title").set_value("   ")
    _button(app, "Generate pre-publication forecast").click().run()
    assert not app.exception
    assert any("title" in info.value.lower() for info in app.info)


def test_ab_comparison_reports_uncertainty(app):
    _button(app, "Compare Draft A and Draft B").click().run()
    assert not app.exception
    assert any("80%" in message.value for message in list(app.info) + list(app.success))
