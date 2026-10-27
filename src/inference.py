"""Safe inference helpers shared by the Streamlit app and automated tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.advanced_model import build_demo_features, normalise_tags  # noqa: F401
from src.insights_artifacts import engagement_interval, views_interval


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = ROOT / "models" / "advanced_model_bundle.joblib"


@dataclass(frozen=True)
class Prediction:
    expected_views: float
    views_low: float
    views_high: float
    engagement_rate: float
    engagement_low: float
    engagement_high: float
    feature_row: pd.DataFrame
    out_of_range_features: tuple[str, ...]
    views_log: float = 0.0
    # Calibrated (split-conformal) 80 % intervals; None if the bundle predates calibration.
    views_ci_low: float | None = None
    views_ci_high: float | None = None
    engagement_ci_low: float | None = None
    engagement_ci_high: float | None = None
    interval_basis: str = "all trending videos"  # or the category name when that category has its own calibrated width


def interval_widths(calibration: dict[str, object], category_name: str) -> tuple[float, float, str]:
    """Interval width for views and engagement: the category's own when it has enough videos, else the overall width.

    One overall width is right on average but wrong for some categories (it used to cover only half of the Gaming videos).
    """
    views_by_category = calibration.get("views_log_q_by_category") or {}
    engagement_by_category = calibration.get("engagement_q_by_category") or {}
    own = category_name in views_by_category
    return (
        float(views_by_category.get(category_name, calibration["views_log_q"])),
        float(engagement_by_category.get(category_name, calibration["engagement_q"])),
        category_name if own else "all trending videos",
    )


def headline_accuracy(bundle: dict[str, object]) -> dict[str, object]:
    """The accuracy numbers to show people, read from the trained bundle (never typed into the app by hand).

    The headline is the test on channels the model had never seen, because that is what a first-time user gets; the shuffled
    cross-validation puts the same channel on both sides of the split and reads higher.  A bundle trained before the
    unseen-channel test existed falls back to the shuffled number and says so.
    """
    views, engagement = bundle["metrics"]["views_log"], bundle["metrics"]["engagement_rate"]
    if "unseen_channel_cv" in views and "unseen_channel_cv" in engagement:
        return {
            "views_r2": views["unseen_channel_cv"]["r2_mean"],
            "engagement_r2": engagement["unseen_channel_cv"]["r2_mean"],
            "basis": "channels the model had never seen",
            "shuffled_views_r2": views["five_fold_cv"]["r2_mean"],
            "shuffled_engagement_r2": engagement["five_fold_cv"]["r2_mean"],
        }
    return {
        "views_r2": views["five_fold_cv"]["r2_mean"],
        "engagement_r2": engagement["five_fold_cv"]["r2_mean"],
        "basis": "shuffled 5-fold cross-validation (optimistic: the same channel is in both halves)",
        "shuffled_views_r2": views["five_fold_cv"]["r2_mean"],
        "shuffled_engagement_r2": engagement["five_fold_cv"]["r2_mean"],
    }


def load_bundle(path: Path = BUNDLE_PATH) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(
            f"Model bundle not found at {path}. Run: python src/advanced_model.py --train"
        )
    bundle = joblib.load(path)
    required = {"models", "input_columns", "numeric_summary", "categories", "metrics"}
    missing = required.difference(bundle)
    if missing:
        raise ValueError(f"Model bundle is missing required fields: {sorted(missing)}")
    wrong = feature_mismatch(bundle["input_columns"])
    if wrong:
        raise ValueError(
            "The saved model was trained with a different set of features than this version of the app uses "
            f"({wrong}). Train it again with: python src/advanced_model.py --train"
        )
    return bundle


def expected_feature_names() -> set[str]:
    """The model inputs the current code builds for a draft (the same function training uses)."""
    return set(build_demo_features("A title", "", "", "Education", 0, 0).columns)


def feature_mismatch(saved_columns: object) -> str:
    """Empty when a saved model's inputs match the code; otherwise a short description of the difference."""
    saved, expected = set(saved_columns), expected_feature_names()
    parts = []
    if expected - saved:
        parts.append("the model lacks " + ", ".join(sorted(expected - saved)))
    if saved - expected:
        parts.append("the model expects " + ", ".join(sorted(saved - expected)))
    return "; ".join(parts)


def predict_frame(bundle: dict[str, object], frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised prediction for many candidate drafts: (log1p views, engagement rate)."""
    features = frame.reindex(columns=list(bundle["input_columns"]))
    models = bundle["models"]
    views_log = np.asarray(models["views_log"].predict(features), dtype=float)
    engagement = np.maximum(0.0, np.asarray(models["engagement_rate"].predict(features), dtype=float))
    return views_log, engagement


def _tree_predictions(model, feature_row: pd.DataFrame) -> np.ndarray:
    preprocessor = model.named_steps["preprocessor"]
    forest = model.named_steps["regressor"]
    transformed = preprocessor.transform(feature_row)
    return np.asarray([tree.predict(transformed)[0] for tree in forest.estimators_], dtype=float)


def _out_of_range_features(feature_row: pd.DataFrame, numeric_summary: dict[str, dict[str, float]]) -> tuple[str, ...]:
    unusual: list[str] = []
    for feature, limits in numeric_summary.items():
        value = float(feature_row.iloc[0][feature])
        if value < limits["p05"] or value > limits["p95"]:
            unusual.append(feature)
    return tuple(unusual)


def predict_video(
    bundle: dict[str, object],
    *,
    title: str,
    tags: str,
    description: str,
    category_name: str,
    day_of_week: int,
    publish_hour: int,
) -> Prediction:
    """Predict a proposed video using the trained feature schema without leakage."""
    if not title.strip():
        raise ValueError("Enter a title before requesting a prediction.")
    if not 0 <= int(day_of_week) <= 6:
        raise ValueError("day_of_week must be in the range 0 (Monday) to 6 (Sunday).")
    if not 0 <= int(publish_hour) <= 23:
        raise ValueError("publish_hour must be in the range 0 to 23.")

    raw_feature_row = build_demo_features(
        title=title,
        tags=normalise_tags(tags),
        description=description,
        category_name=category_name,
        day_of_week=int(day_of_week),
        publish_hour=int(publish_hour),
    )
    input_columns = list(bundle["input_columns"])
    missing = set(input_columns).difference(raw_feature_row.columns)
    unexpected = set(raw_feature_row.columns).difference(input_columns)
    if missing or unexpected:
        raise ValueError(
            "Feature schema mismatch between the app and trained model "
            f"(missing={sorted(missing)}, unexpected={sorted(unexpected)})."
        )
    # The app creates fields in human-readable order; the fitted preprocessor
    # receives the explicit training order stored in the model bundle.
    feature_row = raw_feature_row.reindex(columns=input_columns)

    models = bundle["models"]
    view_model = models["views_log"]
    engagement_model = models["engagement_rate"]
    view_log = float(view_model.predict(feature_row)[0])
    engagement = max(0.0, float(engagement_model.predict(feature_row)[0]))
    view_trees = _tree_predictions(view_model, feature_row)
    engagement_trees = np.maximum(0.0, _tree_predictions(engagement_model, feature_row))

    calibration = bundle.get("calibration")
    ci: dict[str, float | None] = {
        "views_ci_low": None, "views_ci_high": None,
        "engagement_ci_low": None, "engagement_ci_high": None,
    }
    basis = "all trending videos"
    if calibration:
        q_views, q_engagement, basis = interval_widths(calibration, category_name)
        ci["views_ci_low"], ci["views_ci_high"] = views_interval(view_log, q_views)
        ci["engagement_ci_low"], ci["engagement_ci_high"] = engagement_interval(engagement, q_engagement)

    return Prediction(
        views_log=view_log,
        interval_basis=basis,
        **ci,
        expected_views=max(0.0, float(np.expm1(view_log))),
        views_low=max(0.0, float(np.expm1(np.quantile(view_trees, 0.15)))),
        views_high=max(0.0, float(np.expm1(np.quantile(view_trees, 0.85)))),
        engagement_rate=engagement,
        engagement_low=float(np.quantile(engagement_trees, 0.15)),
        engagement_high=float(np.quantile(engagement_trees, 0.85)),
        feature_row=feature_row,
        out_of_range_features=_out_of_range_features(feature_row, bundle["numeric_summary"]),
    )


def global_feature_groups(bundle: dict[str, object]) -> pd.DataFrame:
    """Aggregate forest importances into four easy-to-explain strategy groups."""
    rows: list[dict[str, object]] = []
    for target, model in bundle["models"].items():
        names = model.named_steps["preprocessor"].get_feature_names_out()
        values = model.named_steps["regressor"].feature_importances_
        for name, value in zip(names, values):
            if name.startswith("title_") or name in {"has_number_in_title", "has_question_mark", "caps_ratio"}:
                group = "Title packaging"
            elif name.startswith("tag_"):
                group = "Tags"
            elif name.startswith("description_"):
                group = "Description"
            elif name.startswith("publish_") or name == "is_weekend":
                group = "Publish timing"
            elif name.startswith("category_name_"):
                group = "Category"
            else:
                group = "Other"
            rows.append({"target": target, "group": group, "importance": float(value)})
    return (
        pd.DataFrame(rows)
        .groupby(["target", "group"], as_index=False)["importance"]
        .sum()
        .sort_values(["target", "importance"], ascending=[True, False])
    )
