"""Tests against a REAL local model (Ollama). They run automatically when a local model server is running
and skip otherwise (for example on GitHub Actions). No fake model is used anywhere in this file.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.device_profile import ModelChoice
from src.golden import GOLDEN_DRAFTS
from src.inference import load_bundle, predict_video
from src.recommendations import generate_recommendation, resolve_runtime
from src.reco_schema import validate_recommendation

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
DRAFT = GOLDEN_DRAFTS["education"]
pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def runtime():
    status = resolve_runtime()
    if not status.ready:
        pytest.skip(f"no usable local model: {status.choice.reason}")
    return status


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.fixture(scope="module")
def real_result(bundle, runtime):
    return generate_recommendation(bundle, DRAFT, runtime=runtime)


def test_real_model_answer_is_valid_and_the_forecast_is_untouched(bundle, real_result):
    print(f"\nsource={real_result.source} tier={real_result.tier} model={real_result.model} "
          f"seconds={real_result.seconds:.0f} notice={real_result.notice}")
    assert validate_recommendation(real_result.recommendation, real_result.packet) == []
    direct = predict_video(bundle, title=DRAFT.title, tags=DRAFT.tags, description=DRAFT.description,
                           category_name=DRAFT.category_name, day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
    assert real_result.forecast.expected_views == pytest.approx(direct.expected_views, rel=1e-9)
    for row in real_result.rescored:  # every displayed number is re-scored by the trained model
        check = predict_video(bundle, title=row["draft"].title, tags=row["draft"].tags, description=row["draft"].description,
                              category_name=DRAFT.category_name, day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
        assert row["expected_views"] == pytest.approx(check.expected_views, rel=1e-9)


def test_a_missing_main_model_falls_through_to_the_lite_model_or_rules(bundle, runtime):
    if not runtime.fallback:
        pytest.skip("the lite fallback model is not installed")
    broken = dataclasses.replace(runtime, choice=ModelChoice("no-such-model:1b", "test"))
    result = generate_recommendation(bundle, DRAFT, runtime=broken)
    assert result.tier in {"lite", None}
    if result.source == "llm":
        assert result.model == runtime.fallback and "lite model" in result.notice
    else:
        assert "main model missing" in result.notice


def test_a_real_timeout_falls_back_to_rules(bundle, runtime):
    impatient = dataclasses.replace(runtime, config=dataclasses.replace(runtime.config, timeout_s=0.001))
    result = generate_recommendation(bundle, DRAFT, runtime=impatient)
    assert result.source == "rules" and "too long" in result.notice


def test_a_dead_server_falls_back_to_rules_without_trying_further_models(bundle, runtime):
    dead = dataclasses.replace(runtime, base_url="http://127.0.0.1:9")
    result = generate_recommendation(bundle, DRAFT, runtime=dead)
    assert result.source == "rules" and "No local language model" in result.notice


def test_ai_coach_tab_end_to_end_with_the_real_model(runtime):
    from tests.test_app import write_draft
    from tests.real_videos import REAL_VIDEOS

    app = write_draft(AppTest.from_file(str(APP_PATH), default_timeout=900).run(), REAL_VIDEOS[0])  # the form starts empty
    next(b for b in app.button if b.key == "coach_generate").click().run()
    assert not app.exception
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Expected views (ML model)"] == metrics["Expected views"]
