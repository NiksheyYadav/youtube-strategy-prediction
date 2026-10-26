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
        "Forecast studio", "Best time", "Title lab", "AI coach", "Similar videos", "Scenario lab", "Model brief",
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


# ----------------------------- AI coach tab ----------------------------- #
import json  # noqa: E402

from src.device_profile import DeviceProfile, ModelChoice  # noqa: E402
from src.golden import GOLDEN_DRAFTS  # noqa: E402
from src.inference import load_bundle  # noqa: E402
from src.llm_client import LLMConfig  # noqa: E402
from src.reco_evidence import build_evidence  # noqa: E402
from src.recommendations import RuntimeStatus, rules_recommendation  # noqa: E402

PROFILE = DeviceProfile(ram_gb=16, cpu_threads=16, gpu_name="RTX 5050", gpu_vram_gb=8.0)
NOT_READY = RuntimeStatus(PROFILE, LLMConfig(), None, None, (), ModelChoice(None, "no local model server is running", "ollama pull qwen2.5:7b"))
READY = RuntimeStatus(PROFILE, LLMConfig(), "ollama", "http://127.0.0.1:11434", ("qwen2.5:7b",), ModelChoice("qwen2.5:7b", "test"))


def _coach(monkeypatch, runtime, answer=None):
    monkeypatch.setattr("src.recommendations.resolve_runtime", lambda: runtime)
    if answer is not None:
        monkeypatch.setattr("src.recommendations.generate_json", lambda *args, **kwargs: answer)
    app = AppTest.from_file(str(APP_PATH), default_timeout=180).run()
    next(b for b in app.button if b.key == "coach_generate").click().run()
    return app


def _valid_json(summary=None):
    packet = build_evidence(load_bundle(), GOLDEN_DRAFTS["education"])
    data = rules_recommendation(packet)
    data["title_alternatives"] = [{"title": "5 Study Tips That Really Work for Students", "rationale": "Keeps your own words.", "evidence": ["E1"]}]
    if summary:
        data["summary"] = summary
    return json.dumps(data)


def _texts(app):
    return " ".join(m.value for m in app.markdown) + " " + " ".join(w.value for w in app.warning) + " " + " ".join(i.value for i in app.info)


def test_ai_coach_without_a_local_model_shows_rule_based_advice_and_how_to_enable_the_model(monkeypatch):
    app = _coach(monkeypatch, NOT_READY)
    assert not app.exception
    text = _texts(app)
    assert "Rule-based recommendations" in text and "ollama pull qwen2.5:7b" in text
    assert any(metric.label == "Expected views (ML model)" for metric in app.metric)


def test_ai_coach_with_a_valid_local_model_answer_and_unchanged_forecast(monkeypatch):
    app = _coach(monkeypatch, READY, _valid_json())
    assert not app.exception and "qwen2.5:7b" in _texts(app) and "AI coach" in _texts(app)
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Expected views (ML model)"] == metrics["Expected views"]


def test_ai_coach_falls_back_with_a_notice_when_the_model_returns_garbage(monkeypatch):
    app = _coach(monkeypatch, READY, "I cannot help with that.")
    assert not app.exception
    assert any("evidence checks" in w.value for w in app.warning)
    assert "Rule-based recommendations" in _texts(app)


def test_apply_button_loads_a_re_scored_title_into_the_form(monkeypatch):
    app = _coach(monkeypatch, READY, _valid_json())
    before = app.session_state["main_title"]
    next(b for b in app.button if b.key and b.key.startswith("coach_apply_")).click().run()
    assert not app.exception and app.session_state["main_title"] != before


def test_model_written_markdown_is_escaped(monkeypatch):
    app = _coach(monkeypatch, READY, _valid_json(summary="Use **bold** and _italic_ text."))
    assert not app.exception
    assert r"\*\*bold\*\*" in _texts(app)
