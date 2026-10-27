from pathlib import Path

import pandas as pd
import pytest

from src.channel_history import parse_upload
from src.history_model import load_history_models
from src.inference import load_bundle
from src.insights import Draft
from src.personal_forecast import personal_forecast

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "sample_channel.csv"
DRAFT = Draft("5 Study Tips That Actually Work for Students", "study|tips|students", "Simple tips for exams.", "Education", 5, 18)


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.fixture(scope="module")
def models():
    loaded = load_history_models()
    assert loaded is not None, "models/history_models.joblib is part of the repository"
    return loaded


@pytest.fixture(scope="module")
def sample():
    return parse_upload(SAMPLE.name, SAMPLE.read_bytes())


def test_the_shipped_history_models_report_honest_unseen_channel_results(models):
    unseen = models["metrics"]["unseen_channels"]
    assert unseen["log_views_r2_history_model"] > unseen["log_views_r2_cold_start_model"] + 0.2
    coverage = models["metrics"]["interval_coverage_80"]
    assert 0.75 <= coverage["views_unseen_channels"] <= 0.85


def test_sample_channel_gets_a_forecast_at_its_own_level(bundle, models, sample):
    result = personal_forecast(bundle, models, DRAFT, sample, as_of=pd.Timestamp("2026-10-27", tz="UTC"))
    assert result.reason == "" and result.prediction is not None
    prediction = result.prediction
    assert prediction.n_videos_used == 26
    assert prediction.views_ci_low < prediction.expected_views < prediction.views_ci_high
    # the made-up channel has a few thousand views per video: the forecast must be near that, not near the trending median
    assert 500 < prediction.expected_views < 20_000
    assert 0.2 < prediction.lift_multiplier < 5


def test_studio_export_without_likes_uses_the_trending_model_for_engagement(bundle, models, sample):
    from src.inference import predict_video

    result = personal_forecast(bundle, models, DRAFT, sample, as_of=pd.Timestamp("2026-10-27", tz="UTC"))
    cold = predict_video(bundle, title=DRAFT.title, tags=DRAFT.tags, description=DRAFT.description,
                         category_name=DRAFT.category_name, day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
    prediction = result.prediction
    assert prediction.engagement_source == "trending"
    assert prediction.engagement_rate == pytest.approx(cold.engagement_rate, rel=1e-9)
    assert prediction.engagement_ci_low <= prediction.engagement_rate <= prediction.engagement_ci_high
    assert 0.005 < prediction.engagement_rate < 0.15, "engagement must be a plausible rate, not a filler artefact"


def test_a_bigger_channel_gets_a_proportionally_bigger_forecast(bundle, models, sample):
    as_of = pd.Timestamp("2026-10-27", tz="UTC")
    small = personal_forecast(bundle, models, DRAFT, sample, as_of=as_of).prediction
    bigger = sample.videos.copy()
    bigger["views"] = bigger["views"] * 20
    big_history = type(sample)(bigger, sample.source, sample.hour_known, sample.notes)
    large = personal_forecast(bundle, models, DRAFT, big_history, as_of=as_of).prediction
    assert large.lift_multiplier == pytest.approx(small.lift_multiplier, rel=0.05)  # same draft, same relative effect
    assert large.expected_views / small.expected_views == pytest.approx(20, rel=0.15)


def test_history_that_is_too_recent_is_not_used(bundle, models, sample):
    # on 2026-01-20 only the first video is old enough to count: not enough history
    result = personal_forecast(bundle, models, DRAFT, sample, as_of=pd.Timestamp("2026-01-20", tz="UTC"))
    assert result.prediction is None and result.reason == "not_enough_history"


def test_missing_model_file_degrades_gracefully(bundle, sample):
    result = personal_forecast(bundle, None, DRAFT, sample)
    assert result.prediction is None and result.reason == "no_models"


def test_adding_history_does_not_change_the_trending_video_forecast(bundle, models, sample):
    """The ML numbers of the original model must stay exactly as they were."""
    from src.inference import predict_video

    kwargs = dict(title=DRAFT.title, tags=DRAFT.tags, description=DRAFT.description, category_name=DRAFT.category_name,
                  day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
    before = predict_video(bundle, **kwargs)
    personal_forecast(bundle, models, DRAFT, sample)
    after = predict_video(bundle, **kwargs)
    # equal up to float rounding: the forest adds its trees' answers across threads in a varying order
    assert before.expected_views == pytest.approx(after.expected_views, rel=1e-12)
    assert before.engagement_rate == pytest.approx(after.engagement_rate, rel=1e-12)
