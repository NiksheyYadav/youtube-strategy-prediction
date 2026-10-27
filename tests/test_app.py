"""End-to-end smoke tests: the real Streamlit script is executed headlessly."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.real_data import real_channel, requires_data


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture()
def app():
    return AppTest.from_file(str(APP_PATH), default_timeout=180).run()


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_app_boots_with_every_tab_and_no_exception(app):
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Forecast studio", "My channel", "Best time", "Title lab", "AI coach", "Similar videos", "Scenario lab", "YouTube timeline", "Model brief",
    ]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expected views"] and metrics["Expected engagement"]
    assert "Best slot #1" in metrics
    assert "Expected views for your channel" not in metrics  # nothing is personalised until the creator adds data


@requires_data
def test_a_real_channels_history_personalises_the_forecast_and_can_be_removed(app):
    history = real_channel()
    app.session_state["channel"] = history  # exactly what an upload or the Google connection stores
    app.run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expected views for your channel"] and metrics["Your usual video"]
    assert metrics["This draft vs your usual"].endswith("%")
    assert metrics["Videos loaded"] == str(len(history.videos))
    # the trending-video forecast is still there, unchanged and clearly separate
    assert metrics["Expected views"]
    assert not any("made-up" in warning.value for warning in app.warning), "nothing in the app may be made up"

    _button(app, "Remove my data").click()
    app.run()
    assert not app.exception
    assert "Expected views for your channel" not in {metric.label for metric in app.metric}
    assert "channel" not in app.session_state, "removing the data must really forget it"


def test_personal_forecast_explains_when_there_is_too_little_history(app):
    from src.channel_history import parse_upload

    few = b"Video title,Video publish time,Views\nOnly one,2026-01-02,100\nTwo,2026-01-09,200\n"
    app.session_state["channel"] = parse_upload("few.csv", few)
    app.run()
    assert not app.exception
    assert "Expected views for your channel" not in {metric.label for metric in app.metric}
    assert any("settled" in info.value for info in app.info)


def test_every_real_example_video_produces_a_forecast_and_shows_what_really_happened(app):
    options = list(app.selectbox(key="example_choice").options)
    assert len(options) == 4, "the four real videos from knowledge/real_examples.json"
    for name in options:
        app.selectbox(key="example_choice").select(name).run()
        _button(app, "Load this video").click().run()
        assert not app.exception, name
        assert any(metric.label == "Expected views" for metric in app.metric), name
        banner = " ".join(info.value for info in app.info)
        assert "This is a real video" in banner and "actually got" in banner and "not a fair test" in banner, name


def test_the_real_video_note_disappears_once_the_user_changes_the_title(app):
    assert any("This is a real video" in info.value for info in app.info)
    app.text_area(key="main_title").set_value("Something I wrote myself")  # inside a form the value only counts when submitted
    _button(app, "Generate pre-publication forecast").click().run()
    assert not app.exception
    assert not any("This is a real video" in info.value for info in app.info)


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


# ----------------------------- AI coach tab (rule-based path; real-model tests are in test_real_model.py) ----------------------------- #
from src.device_profile import DeviceProfile, ModelChoice  # noqa: E402
from src.llm_client import LLMConfig  # noqa: E402
from src.recommendations import RuntimeStatus  # noqa: E402

PROFILE = DeviceProfile(ram_gb=16, cpu_threads=16, gpu_name="RTX 5050", gpu_vram_gb=8.0)
NOT_READY = RuntimeStatus(PROFILE, LLMConfig(), None, None, (), ModelChoice(None, "no local model server is running", "ollama pull qwen2.5:7b"))


def _coach_without_model(monkeypatch):
    monkeypatch.setattr("src.recommendations.resolve_runtime", lambda: NOT_READY)
    app = AppTest.from_file(str(APP_PATH), default_timeout=180).run()
    next(b for b in app.button if b.key == "coach_generate").click().run()
    return app


def test_ai_coach_without_a_local_model_shows_rule_based_advice_and_how_to_enable_the_model(monkeypatch):
    app = _coach_without_model(monkeypatch)
    assert not app.exception
    text = " ".join(m.value for m in app.markdown) + " " + " ".join(i.value for i in app.info)
    assert "Rule-based recommendations" in text and "ollama pull qwen2.5:7b" in text
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Expected views (ML model)"] == metrics["Expected views"]


def test_apply_button_loads_a_re_scored_title_into_the_form(monkeypatch):
    app = _coach_without_model(monkeypatch)
    before = app.session_state["main_title"]
    next(b for b in app.button if b.key and b.key.startswith("coach_apply_")).click().run()
    assert not app.exception and app.session_state["main_title"] != before


# ------------------------------------------------------------------ direct YouTube connection (network mocked)
def _history_of(n=5):
    from src.channel_history import clean_videos
    import pandas as pd

    frame = pd.DataFrame({"title": [f"Video {i}" for i in range(n)], "views": [1000 + i for i in range(n)],
                          "publish_time": [f"2026-0{1 + i}-10T10:00:00Z" for i in range(n)]})
    return clean_videos(frame, source="api")


def test_server_without_google_settings_explains_how_to_set_it_up(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    app = AppTest.from_file(str(APP_PATH), default_timeout=180).run()
    assert not app.exception
    assert any("not set up on this server" in caption.value for caption in app.caption)
    assert "Connect with Google" not in [button.label for button in app.button]


def test_connect_button_prepares_a_pkce_login_link_to_google(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-123.apps.googleusercontent.com")
    app = AppTest.from_file(str(APP_PATH), default_timeout=180).run()
    _button(app, "Connect with Google").click()
    app.run()
    assert not app.exception
    url = app.session_state["google_auth_url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "code_challenge_method=S256" in url and "youtube.readonly" in url and "access_type=online" in url


def test_returning_from_google_loads_the_videos_and_cancels_the_access(monkeypatch):
    import src.youtube_api as youtube_api
    import src.youtube_oauth as youtube_oauth

    token = youtube_oauth.TokenSet("ya29.SECRET", float("inf"))
    revoked = []
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-123")
    monkeypatch.setattr(youtube_oauth, "finish_login", lambda config, pending, params, **k: token)
    monkeypatch.setattr(youtube_api, "fetch_channel_history", lambda tok, *a, **k: (_history_of(), {"title": "My *channel*"}))
    monkeypatch.setattr(youtube_oauth, "revoke", lambda tok, **k: revoked.append(tok))
    app = AppTest.from_file(str(APP_PATH), default_timeout=180)
    app.query_params["code"], app.query_params["state"] = "the-code", "the-state"
    app.run()
    assert not app.exception
    assert app.session_state["channel"].source == "api" and len(app.session_state["channel"].videos) == 5
    assert revoked == [token], "the app's access must be cancelled right after the videos are read"
    assert "google_token" not in app.session_state, "no token is kept in the session"
    assert "ya29.SECRET" not in str(app.session_state["channel"])
    assert any("5 videos were read" in success.value for success in app.success)
    assert "code" not in app.query_params and "state" not in app.query_params, "the one-time code must not stay in the address"


def test_a_failed_or_declined_sign_in_shows_a_plain_message_and_loads_nothing(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-123")
    app = AppTest.from_file(str(APP_PATH), default_timeout=180)
    app.query_params["error"], app.query_params["state"] = "access_denied", "whatever"
    app.run()
    assert not app.exception
    assert "channel" not in app.session_state
    assert any("chose not to give access" in error.value for error in app.error)


def test_youtube_timeline_tab_lists_sourced_entries_and_can_hide_press_reports(app):
    text = " ".join(markdown.value for markdown in app.markdown)
    assert "24 Aug 2026" in text and "Source: [YouTube Blog" in text, "entries must show a date and link to their source"
    assert "press report (lower confidence)" in text
    assert "does not publish its ranking formula" in text
    app.checkbox(key="kb_hide_press").check()
    app.run()
    assert not app.exception
    assert "press report (lower confidence)" not in " ".join(markdown.value for markdown in app.markdown)


def test_draft_b_follows_draft_a_until_the_user_edits_it(app):
    """Regression: after loading another video, Draft A changed but Draft B silently kept the old draft."""
    first = app.session_state["main_title"]
    assert app.session_state["compare_title"] == first
    options = list(app.selectbox(key="example_choice").options)
    app.selectbox(key="example_choice").select(options[1]).run()
    _button(app, "Load this video").click().run()
    assert not app.exception
    assert app.session_state["main_title"] != first
    assert app.session_state["compare_title"] == app.session_state["main_title"], "an untouched Draft B must follow Draft A"

    app.text_area(key="compare_title").set_value("My own variant of the title").run()
    app.selectbox(key="example_choice").select(options[2]).run()
    _button(app, "Load this video").click().run()
    assert app.session_state["compare_title"] == "My own variant of the title", "a Draft B the user edited must be left alone"


def test_the_sidebar_is_configured_to_start_closed_on_small_screens():
    source = APP_PATH.read_text(encoding="utf-8")
    assert 'initial_sidebar_state="auto"' in source and 'initial_sidebar_state="expanded"' not in source


def test_a_model_file_that_does_not_match_the_code_gives_a_plain_message_not_a_stack_trace(tmp_path, monkeypatch):
    """The failure a user hit after the code gained a feature while the saved model still lacked it: a raw ValueError page."""
    import joblib
    import streamlit as st

    from src import inference

    saved = joblib.load(inference.BUNDLE_PATH)
    saved["input_columns"] = [name for name in saved["input_columns"] if name != "title_non_latin_share"]
    old_model = tmp_path / "old_model.joblib"
    joblib.dump(saved, old_model)

    real_load = inference.load_bundle
    monkeypatch.setattr(inference, "load_bundle", lambda: real_load(old_model))
    st.cache_resource.clear()
    try:
        broken = AppTest.from_file(str(APP_PATH), default_timeout=180).run()
        assert not broken.exception, "a mismatched model must be explained, not crash the page"
        shown = " ".join(error.value for error in broken.error)
        assert "different set of features" in shown and "advanced_model.py --train" in " ".join(code.value for code in broken.code)
        assert not broken.tabs, "nothing is forecast from a model that does not match the code"
    finally:
        monkeypatch.undo()
        st.cache_resource.clear()
