"""The history-aware model, trained and tested on REAL channels from the dataset (a quick small-forest training, not the shipped model)."""

import joblib
import numpy as np
import pandas as pd
import pytest

from src.advanced_model import build_demo_features
from src.channel_history import history_table
from src.history_features import MISSING_FILL, history_row
from src.history_model import (
    HistoryPrediction,
    lift_features,
    load_history_models,
    predict_with_history,
    train_history_models,
)
from tests.real_data import real_channel, real_training_subset, requires_data

NOW = pd.Timestamp("2026-10-27", tz="UTC")
pytestmark = requires_data


@pytest.fixture(scope="module")
def trained():
    return train_history_models(real_training_subset(n_channels=160), n_estimators=12, n_folds=3)


def _history():
    return history_row(history_table(real_channel(min_videos=10, rank=3)), NOW)


def _draft_row(title="5 Study Tips That Actually Work for Students"):
    return build_demo_features(title, "study tips|productivity", "Simple tips for exams.", "Education", 5, 18)


def test_training_returns_models_calibration_and_metrics(trained):
    assert trained["version"] == 2
    assert set(trained["models"]) == {"views_lift", "engagement"}
    assert trained["calibration"]["views_log_q"] > 0 and trained["calibration"]["engagement_q"] > 0
    metrics = trained["metrics"]
    assert metrics["videos_with_history"] > 500
    assert set(metrics["interval_coverage_80"]) == {"views_unseen_channels", "views_later_videos", "engagement_later_videos"}


def test_engagement_is_only_learned_from_videos_where_it_can_be_measured(trained):
    metrics = trained["metrics"]
    assert 0 < metrics["videos_with_measurable_engagement"] <= metrics["videos_with_history"]
    assert np.isfinite(trained["calibration"]["engagement_q"])
    assert np.isfinite(metrics["unseen_channels"]["engagement_r2_history_model"])


def test_history_beats_the_cold_start_model_on_real_channels_it_never_saw(trained):
    unseen = trained["metrics"]["unseen_channels"]
    assert unseen["log_views_r2_history_model"] > unseen["log_views_r2_cold_start_model"] + 0.15
    assert unseen["log_views_mae_history_model"] < unseen["log_views_mae_cold_start_model"]


def test_prediction_uses_history_and_reports_the_channel_level(trained):
    history = _history()
    prediction = predict_with_history(trained, _draft_row(), history)
    assert isinstance(prediction, HistoryPrediction)
    assert prediction.n_videos_used == history["prior_n"] >= 10
    assert prediction.views_ci_low < prediction.expected_views < prediction.views_ci_high
    assert prediction.engagement_ci_low <= prediction.engagement_rate <= prediction.engagement_ci_high
    # the forecast is the channel's usual level times the model's lift
    assert prediction.expected_views == pytest.approx(prediction.channel_level_views * prediction.lift_multiplier, rel=0.02)


def test_too_little_history_returns_none_so_the_cold_start_model_answers(trained):
    history = _history()
    assert predict_with_history(trained, _draft_row(), {**history, "prior_n": 2.0}) is None
    empty = {"prior_n": 0.0, "prior_missing": 1.0, **{k: MISSING_FILL for k in history if k not in ("prior_n", "prior_missing")}}
    assert predict_with_history(trained, _draft_row(), empty) is None


def test_a_smaller_channel_gets_the_same_lift_at_its_own_level(trained):
    """Level-free by design: making every earlier video ~20x smaller must move the forecast, not change the lift."""
    history = _history()
    small = dict(history)
    for key in ("prior_mean_logviews", "prior_median_logviews", "prior_last_logviews", "prior_max_logviews"):
        small[key] = history[key] - 3.0
    big_prediction = predict_with_history(trained, _draft_row(), history)
    small_prediction = predict_with_history(trained, _draft_row(), small)
    assert small_prediction.lift_multiplier == pytest.approx(big_prediction.lift_multiplier, rel=1e-9)
    assert np.log1p(small_prediction.expected_views) == pytest.approx(np.log1p(big_prediction.expected_views) - 3.0, abs=1e-6)


def test_without_likes_and_comments_the_engagement_forecast_is_withheld_and_views_do_not_change(trained):
    """A Studio export has no likes/comments: the model must not guess engagement from a filler value, and the views
    forecast must not depend on whether engagement history exists."""
    history = _history()
    no_engagement = {**history, "prior_median_engagement": MISSING_FILL}
    with_engagement = predict_with_history(trained, _draft_row(), history)
    without = predict_with_history(trained, _draft_row(), no_engagement)
    assert with_engagement.engagement_source == "history" and np.isfinite(with_engagement.engagement_rate)
    assert without.engagement_source == "unavailable" and np.isnan(without.engagement_rate)
    assert without.expected_views == pytest.approx(with_engagement.expected_views, rel=1e-12)
    assert without.views_ci_low == pytest.approx(with_engagement.views_ci_low, rel=1e-12)


def test_lift_features_never_contain_the_channel_level():
    columns = list(lift_features(pd.DataFrame([_history()])).columns)
    assert not any(name in columns for name in ("prior_mean_logviews", "prior_median_logviews", "prior_last_logviews", "prior_max_logviews"))


def test_save_and_load_round_trip_and_graceful_missing_file(trained, tmp_path):
    path = tmp_path / "history_models.joblib"
    joblib.dump(trained, path)
    loaded = load_history_models(path)
    assert loaded is not None and loaded["min_usable_videos"] == trained["min_usable_videos"]
    assert load_history_models(tmp_path / "missing.joblib") is None
    joblib.dump({"version": 1}, tmp_path / "old.joblib")
    assert load_history_models(tmp_path / "old.joblib") is None
