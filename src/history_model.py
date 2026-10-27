"""Model v2: forecast a new video *relative to the creator's own earlier videos*.

    python -m src.history_model --train          # trains on data/processed/clean.csv, writes models/history_models.joblib

Why "lift": the forecast is  log(views) = (the channel's usual log-views) + lift, and the model only learns the lift
from the draft's content and the shape of the channel's history (spread, trend, how recent the last video is).  The
channel's level itself is never a model input, so a small creator and a huge creator are handled the same way (a forest
cannot predict outside the range it was trained on, but a lift transfers).  Engagement is a rate, so it is predicted
directly with the history features.

Honest limits (also shown in the app): trained on trending videos only, so the lift among creators who never trend
is untested; history needs at least MIN_USABLE_VIDEOS earlier videos, otherwise the cold-start model answers.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold

from src.advanced_model import CATEGORY_COLUMN, CLEAN_PATH, build_feature_table, make_model, model_columns
from src.history_features import HISTORY_COLUMNS, MIN_USABLE_VIDEOS, MISSING_FILL, add_history_features
from src.insights_artifacts import (
    conformal_quantile,
    empirical_coverage,
    engagement_interval,
    engagement_scores,
    views_interval,
    views_scores,
)

ROOT = Path(__file__).resolve().parents[1]
HISTORY_MODELS_PATH = ROOT / "models" / "history_models.joblib"
HISTORY_REPORT_PATH = ROOT / "reports" / "history_model_metrics.json"
RANDOM_STATE = 42


def lift_features(history: pd.DataFrame) -> pd.DataFrame:
    """Level-free description of a channel's history (differences and rates, never the level itself).

    Engagement is left out on purpose: a YouTube Studio export has no likes or comments, and the views forecast must
    not depend on a column that many creators cannot provide.
    """
    mean = history["prior_mean_logviews"]
    return pd.DataFrame({
        "prior_n": history["prior_n"],
        "prior_std_logviews": history["prior_std_logviews"],
        "prior_last_minus_mean": history["prior_last_logviews"] - mean,
        "prior_max_minus_mean": history["prior_max_logviews"] - mean,
        "prior_median_minus_mean": history["prior_median_logviews"] - mean,
        "prior_days_since_last": history["prior_days_since_last"],
        "prior_missing": history["prior_missing"],
    })


def training_history(data: pd.DataFrame) -> pd.DataFrame:
    """History features for the Kaggle trending rows: a video's views are known one day after its last trending day."""
    engagement = (data["likes"].astype(float) + data["comment_count"].astype(float)) / data["views"].astype(float)
    frame = pd.DataFrame({
        "channel_title": data["channel_title"].to_numpy(),
        "publish_time": pd.to_datetime(data["publish_time"], utc=True),
        "known_at": (pd.to_datetime(data["trending_date"]) + pd.Timedelta(days=1)).dt.tz_localize("UTC"),
        "views": data["views"].astype(float).to_numpy(),
        "engagement": engagement.to_numpy(),
    })
    return add_history_features(frame)


def _forest(columns: list[str], n_estimators: int):
    model = make_model([c for c in columns if c != CATEGORY_COLUMN], [CATEGORY_COLUMN])
    model.set_params(regressor__n_estimators=n_estimators, regressor__max_depth=14, regressor__min_samples_leaf=6)
    return model


def train_history_models(
    data: pd.DataFrame,
    *,
    categories: dict[str, str] | None = None,
    n_estimators: int = 120,
    n_folds: int = 5,
) -> dict[str, object]:
    """Train the lift model (views) and the engagement model; calibrate and test them on channels they never saw."""
    table = build_feature_table(data, categories)
    numeric, categorical = model_columns(table)
    content_columns = numeric + categorical
    X_content = table[content_columns].reset_index(drop=True)
    history = training_history(data).reset_index(drop=True)
    usable = np.flatnonzero((history["prior_n"] >= MIN_USABLE_VIDEOS).to_numpy())
    if len(usable) < 50:
        raise ValueError(f"Only {len(usable)} videos have at least {MIN_USABLE_VIDEOS} earlier videos; too few to train.")

    log_views = np.log1p(table["views"].to_numpy(float))
    engagement = table["engagement_rate"].to_numpy(float)
    baseline = history["prior_mean_logviews"].to_numpy()
    X_views = pd.concat([X_content, lift_features(history)], axis=1)
    X_engagement = pd.concat([X_content, history], axis=1)
    lift = log_views - baseline
    channels = data["channel_title"].to_numpy()

    # 1) channels the model has never seen: out-of-fold predictions (also for today's cold-start model, to compare)
    oof_lift = np.full(len(data), np.nan)
    oof_eng = np.full(len(data), np.nan)
    oof_cold = np.full(len(data), np.nan)
    cold_eng = np.full(len(data), np.nan)
    for train_rows, test_rows in GroupKFold(n_splits=n_folds).split(usable, groups=channels[usable]):
        tr, te = usable[train_rows], usable[test_rows]
        oof_lift[te] = _fit(X_views, lift, tr, n_estimators).predict(X_views.iloc[te])
        oof_eng[te] = np.maximum(_fit(X_engagement, engagement, tr, n_estimators).predict(X_engagement.iloc[te]), 0.0)
        oof_cold[te] = _fit(X_content, log_views, tr, n_estimators).predict(X_content.iloc[te])
        cold_eng[te] = np.maximum(_fit(X_content, engagement, tr, n_estimators).predict(X_content.iloc[te]), 0.0)
    pred_log = baseline + oof_lift

    q_views = conformal_quantile(views_scores(log_views[usable], pred_log[usable]))
    q_engagement = conformal_quantile(engagement_scores(engagement[usable], oof_eng[usable]))

    # 2) the same models tested on LATER videos (train on the earliest 80% by publish time)
    order = usable[np.argsort(pd.to_datetime(data["publish_time"], utc=True).to_numpy()[usable], kind="stable")]
    cut = int(len(order) * 0.8)
    early, late = order[:cut], order[cut:]
    late_lift = _fit(X_views, lift, early, n_estimators).predict(X_views.iloc[late])
    late_eng = np.maximum(_fit(X_engagement, engagement, early, n_estimators).predict(X_engagement.iloc[late]), 0.0)
    late_pred = baseline[late] + late_lift
    scale = np.maximum(late_eng, 0.004)

    metrics = {
        "videos_total": int(len(data)),
        "videos_with_history": int(len(usable)),
        "min_usable_videos": MIN_USABLE_VIDEOS,
        "unseen_channels": {
            "log_views_r2_history_model": float(r2_score(log_views[usable], pred_log[usable])),
            "log_views_r2_cold_start_model": float(r2_score(log_views[usable], oof_cold[usable])),
            "log_views_mae_history_model": float(mean_absolute_error(log_views[usable], pred_log[usable])),
            "log_views_mae_cold_start_model": float(mean_absolute_error(log_views[usable], oof_cold[usable])),
            "engagement_r2_history_model": float(r2_score(engagement[usable], oof_eng[usable])),
            "engagement_r2_cold_start_model": float(r2_score(engagement[usable], cold_eng[usable])),
        },
        "later_videos": {
            "log_views_r2_history_model": float(r2_score(log_views[late], late_pred)),
            "engagement_r2_history_model": float(r2_score(engagement[late], late_eng)),
        },
        "interval_coverage_80": {
            "views_unseen_channels": empirical_coverage(log_views[usable], pred_log[usable] - q_views, pred_log[usable] + q_views),
            "views_later_videos": empirical_coverage(log_views[late], late_pred - q_views, late_pred + q_views),
            "engagement_later_videos": empirical_coverage(engagement[late], late_eng - q_engagement * scale, late_eng + q_engagement * scale),
        },
    }
    return {
        "version": 2,
        "models": {
            "views_lift": _fit(X_views, lift, usable, n_estimators),
            "engagement": _fit(X_engagement, engagement, usable, n_estimators),
        },
        "content_columns": content_columns,
        "lift_columns": list(lift_features(history.iloc[:1]).columns),
        "history_columns": list(HISTORY_COLUMNS),
        "min_usable_videos": MIN_USABLE_VIDEOS,
        "calibration": {"views_log_q": float(q_views), "engagement_q": float(q_engagement), "coverage_target": 0.8,
                        "calibrated_on": "out-of-fold predictions for channels never seen in training"},
        "metrics": metrics,
        "trained_rows": int(len(usable)),
        "notes": [
            "Trained on trending videos only: the lift for creators who never trend is untested.",
            "History must contain at least %d earlier videos whose views were already settled." % MIN_USABLE_VIDEOS,
        ],
    }


def _fit(X: pd.DataFrame, y: np.ndarray, rows: np.ndarray, n_estimators: int):
    model = _forest(list(X.columns), n_estimators)
    model.fit(X.iloc[rows], y[rows])
    return model


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HistoryPrediction:
    expected_views: float
    views_ci_low: float
    views_ci_high: float
    engagement_rate: float
    engagement_ci_low: float
    engagement_ci_high: float
    channel_level_views: float  # the creator's usual video (geometric mean of earlier videos)
    lift_multiplier: float      # what the model expects this draft to do relative to that usual video
    n_videos_used: int
    engagement_source: str = "history"  # "history", or "unavailable" when the history has no likes/comments


def load_history_models(path: Path = HISTORY_MODELS_PATH) -> dict[str, object] | None:
    """The history models, or None when the file is missing (the app then keeps using the cold-start model)."""
    try:
        models = joblib.load(path)
    except (OSError, EOFError, ValueError):
        return None
    return models if isinstance(models, dict) and models.get("version") == 2 else None


def predict_with_history(
    models: dict[str, object],
    feature_row: pd.DataFrame,
    history: dict[str, float],
) -> HistoryPrediction | None:
    """Forecast one draft using the creator's history.  ``None`` means "too little history: use the cold-start model"."""
    if history["prior_n"] < int(models["min_usable_videos"]) or history["prior_missing"]:
        return None
    content = feature_row.reindex(columns=models["content_columns"]).reset_index(drop=True)
    history_frame = pd.DataFrame([{name: history[name] for name in models["history_columns"]}])
    lifts = lift_features(history_frame)
    lift = float(models["models"]["views_lift"].predict(pd.concat([content, lifts], axis=1))[0])
    has_engagement = history["prior_median_engagement"] != MISSING_FILL
    engagement = (max(0.0, float(models["models"]["engagement"].predict(pd.concat([content, history_frame], axis=1))[0]))
                  if has_engagement else float("nan"))
    predicted_log = float(history["prior_mean_logviews"]) + lift
    calibration = models["calibration"]
    low, high = views_interval(predicted_log, calibration["views_log_q"])
    eng_low, eng_high = engagement_interval(engagement, calibration["engagement_q"]) if has_engagement else (float("nan"), float("nan"))
    return HistoryPrediction(
        expected_views=max(0.0, float(np.expm1(predicted_log))), views_ci_low=low, views_ci_high=high,
        engagement_rate=engagement, engagement_ci_low=eng_low, engagement_ci_high=eng_high,
        channel_level_views=max(0.0, float(np.expm1(history["prior_mean_logviews"]))),
        lift_multiplier=float(np.exp(lift)), n_videos_used=int(history["prior_n"]),
        engagement_source="history" if has_engagement else "unavailable",
    )


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", action="store_true", help="train and save the history models")
    parser.add_argument("--sample", type=int, default=0, help="train on N random videos only (smoke test; nothing is saved)")
    parser.add_argument("--data", default=str(CLEAN_PATH))
    args = parser.parse_args()
    if not args.train:
        parser.print_help()
        return
    data = pd.read_csv(args.data)
    if args.sample:
        data = data.sample(args.sample, random_state=RANDOM_STATE).reset_index(drop=True)
    models = train_history_models(data, n_estimators=30 if args.sample else 120)
    print(json.dumps(models["metrics"], indent=2))
    if args.sample:
        print("smoke test only: nothing saved")
        return
    HISTORY_MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, HISTORY_MODELS_PATH, compress=3)
    HISTORY_REPORT_PATH.write_text(json.dumps({k: models[k] for k in ("metrics", "calibration", "notes", "trained_rows")}, indent=2), encoding="utf-8")
    print(f"saved {HISTORY_MODELS_PATH} ({HISTORY_MODELS_PATH.stat().st_size / 1e6:.1f} MB) and {HISTORY_REPORT_PATH}")


if __name__ == "__main__":
    main()
