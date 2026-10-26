"""Train and evaluate explainable, leakage-safe Random Forest / XGBoost models.

Version 2 adds title, tag, description, and cyclic time features while keeping
all post-publication columns outside the input matrix.  It saves separate v2
artifacts so the original project models remain available as a fallback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from xgboost import XGBRegressor

from model_contract import (
    FEATURE_VERSION,
    RAW_MODEL_COLUMNS,
    build_training_design_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = ROOT / "data" / "processed" / "advanced_features.csv"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
METRICS_PATH = REPORTS_DIR / "advanced_metrics.json"
SCHEMA_PATH = MODELS_DIR / "feature_schema_v2.json"
RANDOM_STATE = 42


def load_feature_table() -> pd.DataFrame:
    if not FEATURES_PATH.exists():
        raise SystemExit(f"{FEATURES_PATH} not found. Run src/advanced_features.py first.")
    return pd.read_csv(FEATURES_PATH)


def model_factories() -> dict[str, Callable[[], object]]:
    return {
        "random_forest": lambda: RandomForestRegressor(
            n_estimators=350,
            max_depth=18,
            min_samples_leaf=3,
            max_features=0.8,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "xgboost": lambda: XGBRegressor(
            n_estimators=350,
            max_depth=6,
            learning_rate=0.04,
            min_child_weight=4,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=2.0,
            objective="reg:squarederror",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def metric_dict(y_true: pd.Series, predictions: np.ndarray) -> dict[str, float]:
    return {
        "r2": float(r2_score(y_true, predictions)),
        "mae": float(mean_absolute_error(y_true, predictions)),
    }


def evaluate_cross_validation(
    factory: Callable[[], object], X: pd.DataFrame, y: pd.Series
) -> dict[str, float]:
    folds = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    fold_metrics = []
    for train_indices, validation_indices in folds.split(X):
        model = factory()
        model.fit(X.iloc[train_indices], y.iloc[train_indices])
        fold_metrics.append(
            metric_dict(y.iloc[validation_indices], model.predict(X.iloc[validation_indices]))
        )
    return {
        "r2_mean": float(np.mean([item["r2"] for item in fold_metrics])),
        "r2_std": float(np.std([item["r2"] for item in fold_metrics])),
        "mae_mean": float(np.mean([item["mae"] for item in fold_metrics])),
        "mae_std": float(np.std([item["mae"] for item in fold_metrics])),
    }


def evaluate_chronological_holdout(
    factory: Callable[[], object],
    X: pd.DataFrame,
    y: pd.Series,
    published_at: pd.Series,
) -> dict[str, float | str | int]:
    """Train on the oldest 80% of uploads and test on the newest 20%."""
    ordering = pd.to_datetime(published_at, utc=True).sort_values().index
    split_at = int(len(ordering) * 0.8)
    train_indices, test_indices = ordering[:split_at], ordering[split_at:]
    model = factory()
    model.fit(X.loc[train_indices], y.loc[train_indices])
    result: dict[str, float | str | int] = metric_dict(y.loc[test_indices], model.predict(X.loc[test_indices]))
    result.update(
        {
            "train_rows": int(len(train_indices)),
            "test_rows": int(len(test_indices)),
            "test_period_start": str(pd.to_datetime(published_at.loc[test_indices], utc=True).min().date()),
            "test_period_end": str(pd.to_datetime(published_at.loc[test_indices], utc=True).max().date()),
        }
    )
    return result


def run_target(
    target_name: str,
    X: pd.DataFrame,
    y: pd.Series,
    published_at: pd.Series,
) -> tuple[dict, object]:
    factories = model_factories()
    baseline_train, baseline_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    baseline = LinearRegression().fit(baseline_train, y_train)
    baseline_metrics = metric_dict(y_test, baseline.predict(baseline_test))

    cv_results = {
        name: evaluate_cross_validation(factory, X, y)
        for name, factory in factories.items()
    }
    best_name = max(cv_results, key=lambda name: cv_results[name]["r2_mean"])
    champion_factory = factories[best_name]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    champion = champion_factory()
    champion.fit(X_train, y_train)
    held_out_metrics = metric_dict(y_test, champion.predict(X_test))
    chronological_metrics = evaluate_chronological_holdout(
        champion_factory, X, y, published_at
    )

    final_model = champion_factory()
    final_model.fit(X, y)
    model_path = MODELS_DIR / f"{target_name}_model_v2.pkl"
    joblib.dump(final_model, model_path)

    return (
        {
            "baseline_linear_regression": baseline_metrics,
            "cv_results": cv_results,
            "best_model": best_name,
            "held_out_test": held_out_metrics,
            "chronological_holdout": chronological_metrics,
            "model_path": str(model_path.relative_to(ROOT)).replace("\\", "/"),
        },
        final_model,
    )


def main() -> None:
    table = load_feature_table()
    X = build_training_design_matrix(table)
    y_views_log = np.log1p(table["views"])
    y_engagement = table["engagement_rate"]
    published_at = table["published_at_utc"]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    views_result, views_model = run_target("views", X, y_views_log, published_at)
    engagement_result, engagement_model = run_target(
        "engagement_rate", X, y_engagement, published_at
    )
    metrics = {
        "feature_version": FEATURE_VERSION,
        "dataset_rows": int(len(table)),
        "input_policy": "Only metadata known before publication is included as input.",
        "views": {**views_result, "target_scale": "log1p(views)"},
        "engagement_rate": engagement_result,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    schema = {
        "feature_version": FEATURE_VERSION,
        "raw_feature_columns": RAW_MODEL_COLUMNS,
        "design_matrix_columns": list(X.columns),
        "known_categories": sorted(table["category_name"].dropna().unique().tolist()),
        "models": {
            "views": {
                "path": views_result["model_path"],
                "model_type": views_result["best_model"],
                "target_scale": "log1p(views)",
                "supports_tree_spread": hasattr(views_model, "estimators_"),
            },
            "engagement_rate": {
                "path": engagement_result["model_path"],
                "model_type": engagement_result["best_model"],
                "target_scale": "rate",
                "supports_tree_spread": hasattr(engagement_model, "estimators_"),
            },
        },
    }
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved model contract to {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
