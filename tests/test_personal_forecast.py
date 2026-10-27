"""Personalised forecasts, tested on the history of a REAL channel from the dataset (not an invented one)."""

import numpy as np
import pandas as pd
import pytest

from src.channel_history import ChannelHistory, summarise
from src.history_model import load_history_models
from src.inference import load_bundle, predict_video
from src.insights import Draft
from src.personal_forecast import personal_forecast
from tests.real_data import real_channel, requires_data

DRAFT = Draft("5 Study Tips That Actually Work for Students", "study tips|productivity", "Simple tips for exams.", "Education", 5, 18)
NOW = pd.Timestamp("2026-10-27", tz="UTC")


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.fixture(scope="module")
def models():
    loaded = load_history_models()
    assert loaded is not None, "models/history_models.joblib is part of the repository"
    return loaded


@pytest.fixture(scope="module")
def channel():
    return real_channel()


def test_the_shipped_history_models_report_honest_unseen_channel_results(models):
    unseen = models["metrics"]["unseen_channels"]
    assert unseen["log_views_r2_history_model"] > unseen["log_views_r2_cold_start_model"] + 0.2
    coverage = models["metrics"]["interval_coverage_80"]
    assert 0.75 <= coverage["views_unseen_channels"] <= 0.85


@requires_data
def test_a_real_channel_gets_a_forecast_at_its_own_level(bundle, models, channel):
    result = personal_forecast(bundle, models, DRAFT, channel, as_of=NOW)
    assert result.reason == "" and result.prediction is not None
    prediction = result.prediction
    typical = summarise(channel)["typical_views"]
    assert prediction.n_videos_used >= 20
    assert prediction.views_ci_low < prediction.expected_views < prediction.views_ci_high
    assert 0.1 * typical < prediction.expected_views < 10 * typical, "the forecast must sit near this channel's own level"
    assert 0.2 < prediction.lift_multiplier < 5


@requires_data
def test_a_real_channel_with_likes_and_comments_gets_an_engagement_forecast_from_its_own_history(bundle, models, channel):
    prediction = personal_forecast(bundle, models, DRAFT, channel, as_of=NOW).prediction
    assert prediction.engagement_source == "history" and 0 < prediction.engagement_rate < 0.5


@requires_data
def test_an_export_without_likes_uses_the_trending_model_for_engagement(bundle, models):
    studio_like = real_channel(with_reactions=False)  # the same real videos, but only what a Studio table has: title, date, views
    prediction = personal_forecast(bundle, models, DRAFT, studio_like, as_of=NOW).prediction
    cold = predict_video(bundle, title=DRAFT.title, tags=DRAFT.tags, description=DRAFT.description, category_name=DRAFT.category_name,
                         day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
    assert prediction.engagement_source == "trending"
    assert prediction.engagement_rate == pytest.approx(cold.engagement_rate, rel=1e-9)
    assert prediction.engagement_ci_low <= prediction.engagement_rate <= prediction.engagement_ci_high
    assert 0.005 < prediction.engagement_rate < 0.15, "engagement must be a plausible rate, not a placeholder artefact"


@requires_data
def test_a_channel_twenty_times_bigger_gets_a_proportionally_bigger_forecast(bundle, models, channel):
    small = personal_forecast(bundle, models, DRAFT, channel, as_of=NOW).prediction
    bigger = channel.videos.copy()
    bigger["views"] = bigger["views"] * 20
    large = personal_forecast(bundle, models, DRAFT, ChannelHistory(bigger, channel.source, channel.hour_known, channel.notes), as_of=NOW).prediction
    assert large.lift_multiplier == pytest.approx(small.lift_multiplier, rel=0.05)  # same draft, same relative effect
    assert large.expected_views / small.expected_views == pytest.approx(20, rel=0.15)


@requires_data
def test_videos_whose_views_have_not_settled_are_not_used(bundle, models, channel):
    second_video = channel.videos["publish_time"].iloc[1]
    result = personal_forecast(bundle, models, DRAFT, channel, as_of=second_video)  # at that moment at most one video is old enough
    assert result.prediction is None and result.reason == "not_enough_history"


@requires_data
def test_a_missing_model_file_degrades_gracefully(bundle, channel):
    result = personal_forecast(bundle, None, DRAFT, channel)
    assert result.prediction is None and result.reason == "no_models"


@requires_data
def test_adding_history_does_not_change_the_trending_video_forecast(bundle, models, channel):
    """The ML numbers of the original model must stay exactly as they were."""
    kwargs = dict(title=DRAFT.title, tags=DRAFT.tags, description=DRAFT.description, category_name=DRAFT.category_name,
                  day_of_week=DRAFT.day_of_week, publish_hour=DRAFT.publish_hour)
    before = predict_video(bundle, **kwargs)
    personal_forecast(bundle, models, DRAFT, channel)
    after = predict_video(bundle, **kwargs)
    # equal up to float rounding: the forest adds its trees' answers across threads in a varying order
    assert before.expected_views == pytest.approx(after.expected_views, rel=1e-12)
    assert before.engagement_rate == pytest.approx(after.engagement_rate, rel=1e-12)


@requires_data
def test_forecasts_for_several_real_channels_are_ordered_like_the_channels(bundle, models):
    """Real channels of very different size must get forecasts of very different size, in the same order."""
    pairs = []
    for rank in (0, 5, 15, 40):
        history = real_channel(min_videos=10, rank=rank)
        prediction = personal_forecast(bundle, models, DRAFT, history, as_of=NOW).prediction
        pairs.append((summarise(history)["typical_views"], prediction.expected_views))
    pairs.sort()
    forecasts = [forecast for _, forecast in pairs]
    assert np.corrcoef(np.log([t for t, _ in pairs]), np.log(forecasts))[0, 1] > 0.9
