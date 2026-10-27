import joblib
import numpy as np
import pandas as pd
import pytest

from src.advanced_model import build_demo_features
from src.history_features import MISSING_FILL, history_row
from src.history_model import (
    HistoryPrediction,
    lift_features,
    load_history_models,
    predict_with_history,
    train_history_models,
    training_history,
)

CATEGORIES = {"10": "Music"}


def synthetic_channels(n_channels: int = 36, per_channel: int = 14, seed: int = 0) -> pd.DataFrame:
    """Channels with very different levels; a number in the title adds a small lift."""
    rng = np.random.default_rng(seed)
    rows = []
    for channel in range(n_channels):
        level = rng.normal(11.0, 1.6)
        for step in range(per_channel):
            has_number = bool(rng.integers(0, 2))
            views = np.expm1(level + 0.35 * has_number + rng.normal(0, 0.25))
            published = pd.Timestamp("2018-01-01", tz="UTC") + pd.Timedelta(days=9 * step + channel % 5)
            rows.append({
                "video_id": f"v{channel}-{step}", "channel_title": f"channel {channel}",
                "title": f"{'7 ' if has_number else ''}tips for video {step}", "tags": "a|b|c", "description": "plain description",
                "category_id": "10", "publish_time": published.isoformat(),
                "trending_date": (published + pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
                "views": views, "likes": views * 0.03, "comment_count": views * 0.004,
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def trained():
    return train_history_models(synthetic_channels(), categories=CATEGORIES, n_estimators=12, n_folds=3)


def test_training_returns_models_calibration_and_metrics(trained):
    assert trained["version"] == 2
    assert set(trained["models"]) == {"views_lift", "engagement"}
    assert trained["calibration"]["views_log_q"] > 0 and trained["calibration"]["engagement_q"] > 0
    metrics = trained["metrics"]
    assert metrics["videos_with_history"] > 100
    assert set(metrics["interval_coverage_80"]) == {"views_unseen_channels", "views_later_videos", "engagement_later_videos"}


def test_history_beats_the_cold_start_model_on_channels_it_never_saw(trained):
    unseen = trained["metrics"]["unseen_channels"]
    assert unseen["log_views_r2_history_model"] > unseen["log_views_r2_cold_start_model"] + 0.3
    assert unseen["log_views_mae_history_model"] < unseen["log_views_mae_cold_start_model"]


def _history_for(published="2018-06-01"):
    data = synthetic_channels(n_channels=1, per_channel=8, seed=5)
    frame = training_history(data)  # the same rows the model was trained on, for one channel
    history = pd.DataFrame({
        "publish_time": pd.to_datetime(data["publish_time"], utc=True),
        "known_at": pd.to_datetime(data["trending_date"]).dt.tz_localize("UTC") + pd.Timedelta(days=1),
        "views": data["views"], "engagement": (data["likes"] + data["comment_count"]) / data["views"],
    })
    return history_row(history, pd.Timestamp(published, tz="UTC")), frame


def _draft_row(title="7 tips for video 99"):
    return build_demo_features(title, "a|b|c", "plain description", "Music", 5, 18)


def test_prediction_uses_history_and_reports_the_channel_level(trained):
    history, _ = _history_for()
    prediction = predict_with_history(trained, _draft_row(), history)
    assert isinstance(prediction, HistoryPrediction)
    assert prediction.n_videos_used == 8
    assert prediction.views_ci_low < prediction.expected_views < prediction.views_ci_high
    assert prediction.engagement_ci_low <= prediction.engagement_rate <= prediction.engagement_ci_high
    # the forecast is the channel's usual level times the model's lift
    assert prediction.expected_views == pytest.approx(prediction.channel_level_views * prediction.lift_multiplier, rel=0.02)


def test_too_little_history_returns_none_so_the_cold_start_model_answers(trained):
    history, _ = _history_for()
    assert predict_with_history(trained, _draft_row(), {**history, "prior_n": 2.0}) is None
    empty = {"prior_n": 0.0, "prior_missing": 1.0, **{k: MISSING_FILL for k in history if k not in ("prior_n", "prior_missing")}}
    assert predict_with_history(trained, _draft_row(), empty) is None


def test_a_smaller_channel_gets_the_same_lift_at_its_own_level(trained):
    """Level-free by design: making every earlier video ~20x smaller must move the forecast, not change the lift."""
    history, _ = _history_for()
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
    history, _ = _history_for()
    no_engagement = {**history, "prior_median_engagement": MISSING_FILL}
    with_engagement = predict_with_history(trained, _draft_row(), history)
    without = predict_with_history(trained, _draft_row(), no_engagement)
    assert with_engagement.engagement_source == "history" and np.isfinite(with_engagement.engagement_rate)
    assert without.engagement_source == "unavailable" and np.isnan(without.engagement_rate)
    assert without.expected_views == pytest.approx(with_engagement.expected_views, rel=1e-12)
    assert without.views_ci_low == pytest.approx(with_engagement.views_ci_low, rel=1e-12)


def test_lift_features_never_contain_the_channel_level():
    history, _ = _history_for()
    columns = list(lift_features(pd.DataFrame([history])).columns)
    assert not any(name in columns for name in ("prior_mean_logviews", "prior_median_logviews", "prior_last_logviews", "prior_max_logviews"))


def test_save_and_load_round_trip_and_graceful_missing_file(trained, tmp_path):
    path = tmp_path / "history_models.joblib"
    joblib.dump(trained, path)
    loaded = load_history_models(path)
    assert loaded is not None and loaded["min_usable_videos"] == trained["min_usable_videos"]
    assert load_history_models(tmp_path / "missing.joblib") is None
    joblib.dump({"version": 1}, tmp_path / "old.joblib")
    assert load_history_models(tmp_path / "old.joblib") is None
