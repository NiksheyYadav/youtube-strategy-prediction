"""Stage 3 + 4: baseline Linear Regression, then Random Forest / XGBoost with 5-fold CV."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from xgboost import XGBRegressor

FEATURES_PATH = Path("data/processed/features.csv")
BASELINE_METRICS_PATH = Path("reports/baseline_metrics.json")
MAIN_METRICS_PATH = Path("reports/main_metrics.json")
MODELS_DIR = Path("models")

RANDOM_STATE = 42
INPUT_COLUMNS = [
    "title_length",
    "title_word_count",
    "has_number_in_title",
    "has_question_mark",
    "caps_ratio",
    "tag_count",
    "category_name",
    "publish_day_of_week",
    "publish_hour",
    "description_length",
]


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"{path} not found — run src/features.py first.")
    return pd.read_csv(path)


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    X = df[INPUT_COLUMNS].copy()
    X["has_number_in_title"] = X["has_number_in_title"].astype(int)
    X["has_question_mark"] = X["has_question_mark"].astype(int)
    X = pd.get_dummies(X, columns=["category_name"], drop_first=True)

    y_views_log = np.log1p(df["views"])
    y_engagement = df["engagement_rate"]
    return X, y_views_log, y_engagement


def run_baseline(X: pd.DataFrame, y: pd.Series) -> dict:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    return {"r2": r2_score(y_test, preds), "mae": mean_absolute_error(y_test, preds)}


def cross_validate(model_factory, X: pd.DataFrame, y: pd.Series) -> dict:
    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    r2_scores, mae_scores = [], []
    for train_idx, val_idx in kf.split(X):
        model = model_factory()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = model.predict(X.iloc[val_idx])
        r2_scores.append(r2_score(y.iloc[val_idx], preds))
        mae_scores.append(mean_absolute_error(y.iloc[val_idx], preds))
    return {
        "r2_mean": float(np.mean(r2_scores)),
        "r2_std": float(np.std(r2_scores)),
        "mae_mean": float(np.mean(mae_scores)),
        "mae_std": float(np.std(mae_scores)),
    }


def run_main_model(X: pd.DataFrame, y: pd.Series, target_name: str) -> dict:
    factories = {
        "random_forest": lambda: RandomForestRegressor(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "xgboost": lambda: XGBRegressor(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
        ),
    }
    cv_results = {name: cross_validate(f, X, y) for name, f in factories.items()}
    best_name = max(cv_results, key=lambda n: cv_results[n]["r2_mean"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    best_model = factories[best_name]()
    best_model.fit(X_train, y_train)
    preds = best_model.predict(X_test)
    test_metrics = {"r2": r2_score(y_test, preds), "mae": mean_absolute_error(y_test, preds)}

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"{target_name}_model.pkl"
    joblib.dump(best_model, model_path)

    return {
        "cv_results": cv_results,
        "best_model": best_name,
        "test_metrics": test_metrics,
        "model_path": str(model_path),
    }


def main() -> None:
    df = load(FEATURES_PATH)
    X, y_views_log, y_engagement = prepare_features(df)

    print("=== Stage 3: Baseline Linear Regression ===")
    baseline_metrics = {
        "views": {**run_baseline(X, y_views_log), "scale": "log1p(views)"},
        "engagement_rate": run_baseline(X, y_engagement),
    }
    print(json.dumps(baseline_metrics, indent=2))
    BASELINE_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_METRICS_PATH.write_text(json.dumps(baseline_metrics, indent=2))
    print(f"Saved baseline metrics to {BASELINE_METRICS_PATH.resolve()}")

    print("\n=== Stage 4: Random Forest + XGBoost (5-fold CV) ===")
    main_metrics = {
        "views": {**run_main_model(X, y_views_log, "views"), "scale": "log1p(views)"},
        "engagement_rate": run_main_model(X, y_engagement, "engagement_rate"),
    }
    print(json.dumps(main_metrics, indent=2))
    MAIN_METRICS_PATH.write_text(json.dumps(main_metrics, indent=2))
    print(f"Saved main model metrics to {MAIN_METRICS_PATH.resolve()}")


if __name__ == "__main__":
    main()
