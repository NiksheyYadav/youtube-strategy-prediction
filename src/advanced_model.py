"""Train the explainable, pre-publication-only model used in the TA4 demo.

The original model remains a valid baseline.  This module adds transparent
content, tag, and timing features that can be computed before upload, then
tests the model with both random five-fold CV and a chronological holdout.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    from src import insights_artifacts as artifacts
except ModuleNotFoundError:  # run directly as: python src/advanced_model.py
    import insights_artifacts as artifacts


ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "processed" / "clean.csv"
CATEGORY_PATH = ROOT / "data" / "IN_category_id.json"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
BUNDLE_PATH = MODELS_DIR / "advanced_model_bundle.joblib"
SIMILARITY_PATH = MODELS_DIR / "similarity_index.joblib"
CALIBRATION_PATH = REPORTS_DIR / "calibration_report.json"
METRICS_PATH = REPORTS_DIR / "advanced_model_metrics.json"
IMPORTANCE_PATH = REPORTS_DIR / "advanced_feature_importance.png"
GROUP_IMPORTANCE_PATH = REPORTS_DIR / "feature_group_importance.csv"
MODEL_CARD_PATH = REPORTS_DIR / "advanced_model_card.md"

RANDOM_STATE = 42
TARGET_COLUMNS = ["views", "engagement_rate"]
CATEGORY_COLUMN = "category_name"

POSITIVE_WORDS = {
    "amazing", "best", "easy", "exclusive", "free", "fun", "great", "guide",
    "helpful", "love", "new", "perfect", "powerful", "secret", "simple", "top",
    "ultimate", "win", "wow",
}
NEGATIVE_WORDS = {
    "bad", "fail", "fake", "hate", "mistake", "problem", "scam", "shocking",
    "worst", "wrong",
}
URGENCY_WORDS = {
    "alert", "breaking", "exclusive", "final", "important", "latest", "live",
    "must", "new", "now", "official", "today", "update", "urgent",
}
HOW_TO_WORDS = {"how", "tutorial", "guide", "tips", "trick", "learn", "steps"}
CTA_WORDS = {"subscribe", "comment", "like", "share", "follow", "download", "watch"}
LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<!\w)#\w+")


@dataclass(frozen=True)
class Metrics:
    r2: float
    mae: float


# The Kaggle JSON omits id 29, which YouTube's official category list names "Nonprofits & Activism".
SUPPLEMENTAL_CATEGORIES = {"29": "Nonprofits & Activism"}


def category_mapping(path: Path = CATEGORY_PATH) -> dict[str, str]:
    """Return YouTube category names indexed by their API IDs."""
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    mapping = {str(item["id"]): item["snippet"]["title"] for item in payload["items"]}
    for category_id, name in SUPPLEMENTAL_CATEGORIES.items():
        mapping.setdefault(category_id, name)
    return mapping


def _tokens(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", str(value).lower())


def normalise_tags(tags: object) -> str:
    """Accept commas, semicolons, newlines or pipes; return the pipe form used in training."""
    if tags is None or (isinstance(tags, float) and pd.isna(tags)):
        return "[none]"
    parts = re.split(r"[|;,\n]", str(tags))
    return "|".join(part.strip().strip('"') for part in parts if part.strip().strip('"')) or "[none]"


def _tag_parts(value: object) -> list[str]:
    """Training tags are pipe-separated and many carry literal quotes; live input has none."""
    if pd.isna(value) or str(value).strip().lower() in {"", "[none]"}:
        return []
    return [part.strip().strip('"').strip() for part in str(value).split("|") if part.strip().strip('"').strip()]


def _caps_ratio(value: str) -> float:
    letters = [character for character in str(value) if character.isalpha()]
    return sum(character.isupper() for character in letters) / len(letters) if letters else 0.0


def _emoji_count(value: str) -> int:
    return sum(
        unicodedata.category(character) == "So" and ord(character) > 10_000
        for character in str(value)
    )


def _lexical_diversity(tokens: Iterable[str]) -> float:
    tokens = list(tokens)
    return len(set(tokens)) / len(tokens) if tokens else 0.0


def _keyword_count(tokens: Iterable[str], keywords: set[str]) -> int:
    return sum(token in keywords for token in tokens)


def _content_features(
    title: str,
    tags: object,
    description: str,
    category_name: str,
    day_of_week: int,
    publish_hour: int,
) -> dict[str, object]:
    """Build only signals known before a video is uploaded."""
    title = str(title or "")
    description = str(description or "")
    title_tokens = _tokens(title)
    description_tokens = _tokens(description)
    tag_parts = _tag_parts(tags)
    title_word_lengths = [len(token) for token in title_tokens]
    tag_lengths = [len(tag) for tag in tag_parts]
    sentiment_denominator = max(len(title_tokens), 1)

    return {
        # Existing baseline features retained for comparability.
        "title_length": len(title),
        "title_word_count": len(title_tokens),
        "has_number_in_title": int(any(character.isdigit() for character in title)),
        "has_question_mark": int("?" in title),
        "caps_ratio": _caps_ratio(title),
        "tag_count": len(tag_parts),
        "description_length": len(description),
        CATEGORY_COLUMN: category_name or "Unknown",
        "publish_day_of_week": int(day_of_week),
        "publish_hour": int(publish_hour),
        # New, explainable title signals.
        "title_exclamation_count": title.count("!"),
        "title_question_count": title.count("?"),
        "title_punctuation_count": sum(character in "!?.,:-" for character in title),
        "title_emoji_count": _emoji_count(title),
        "title_digit_count": sum(character.isdigit() for character in title),
        "title_avg_word_length": float(np.mean(title_word_lengths)) if title_word_lengths else 0.0,
        "title_lexical_diversity": _lexical_diversity(title_tokens),
        "title_sentiment_score": (
            _keyword_count(title_tokens, POSITIVE_WORDS) - _keyword_count(title_tokens, NEGATIVE_WORDS)
        ) / sentiment_denominator,
        "title_urgency_words": _keyword_count(title_tokens, URGENCY_WORDS),
        "title_how_to_words": _keyword_count(title_tokens, HOW_TO_WORDS),
        # New, explainable tag and description signals.
        "tag_total_characters": sum(tag_lengths),
        "tag_avg_length": float(np.mean(tag_lengths)) if tag_lengths else 0.0,
        "tag_multiword_ratio": (
            sum(" " in tag for tag in tag_parts) / len(tag_parts) if tag_parts else 0.0
        ),
        "description_word_count": len(description_tokens),
        "description_link_count": len(LINK_RE.findall(description)),
        "description_hashtag_count": len(HASHTAG_RE.findall(description)),
        "description_cta_count": _keyword_count(description_tokens, CTA_WORDS),
        # Cyclical timing makes 23:00 close to 00:00 for a tree model.
        "is_weekend": int(int(day_of_week) >= 5),
        "publish_hour_sin": float(np.sin(2 * np.pi * int(publish_hour) / 24)),
        "publish_hour_cos": float(np.cos(2 * np.pi * int(publish_hour) / 24)),
    }


def build_feature_table(
    data: pd.DataFrame,
    categories: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Create model inputs plus targets from de-duplicated raw video records."""
    categories = categories or category_mapping()
    publish_time = pd.to_datetime(data["publish_time"], utc=True, errors="coerce")
    publish_ist = publish_time + pd.Timedelta(hours=5.5)
    category_names = (
        data["category_id"].astype(str).map(categories).fillna("Unknown")
        if "category_id" in data
        else data[CATEGORY_COLUMN].fillna("Unknown")
    )
    rows = [
        _content_features(title, tags, description, category, day, hour)
        for title, tags, description, category, day, hour in zip(
            data["title"].fillna(""),
            data["tags"].fillna("[none]"),
            data["description"].fillna(""),
            category_names,
            publish_ist.dt.dayofweek.fillna(0).astype(int),
            publish_ist.dt.hour.fillna(0).astype(int),
        )
    ]
    feature_table = pd.DataFrame(rows)
    feature_table["views"] = data["views"].astype(float).to_numpy()
    feature_table["engagement_rate"] = (
        (data["likes"].astype(float) + data["comment_count"].astype(float))
        / data["views"].astype(float)
    ).to_numpy()
    feature_table["publish_timestamp"] = publish_time.to_numpy()
    return feature_table


def build_demo_features(
    title: str,
    tags: str,
    description: str,
    category_name: str,
    day_of_week: int,
    publish_hour: int,
) -> pd.DataFrame:
    """Use the exact same feature code for a live user entry as for training."""
    return pd.DataFrame(
        [_content_features(title, normalise_tags(tags), description, category_name, day_of_week, publish_hour)]
    )


def model_columns(feature_table: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical = [CATEGORY_COLUMN]
    numeric = [
        column
        for column in feature_table.columns
        if column not in set(TARGET_COLUMNS + ["publish_timestamp"] + categorical)
    ]
    return numeric, categorical


def make_model(numeric_columns: list[str], categorical_columns: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        [("category", OneHotEncoder(handle_unknown="ignore"), categorical_columns)],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    forest = RandomForestRegressor(
        n_estimators=180,
        max_depth=16,
        min_samples_leaf=5,
        max_features=0.8,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("regressor", forest)])


def _evaluate(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> Metrics:
    predictions = model.predict(X)
    return Metrics(r2=float(r2_score(y, predictions)), mae=float(mean_absolute_error(y, predictions)))


def evaluate_target(
    template: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    timestamps: pd.Series,
) -> tuple[dict[str, object], np.ndarray, np.ndarray, np.ndarray]:
    """Report shuffled CV and an honest later-in-time holdout.

    Also returns the out-of-fold predictions and the chronological-holdout
    predictions, which the calibration step needs.
    """
    folds = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores: list[Metrics] = []
    out_of_fold = np.zeros(len(X), dtype=float)
    for train_index, validation_index in folds.split(X):
        fold_model = clone(template)
        fold_model.fit(X.iloc[train_index], y.iloc[train_index])
        out_of_fold[validation_index] = fold_model.predict(X.iloc[validation_index])
        scores.append(_evaluate(fold_model, X.iloc[validation_index], y.iloc[validation_index]))

    order = np.argsort(pd.to_datetime(timestamps, utc=True).astype("int64").to_numpy())
    split = int(len(order) * 0.8)
    holdout_index = order[split:]
    temporal_model = clone(template)
    temporal_model.fit(X.iloc[order[:split]], y.iloc[order[:split]])
    temporal = _evaluate(temporal_model, X.iloc[holdout_index], y.iloc[holdout_index])
    holdout_prediction = temporal_model.predict(X.iloc[holdout_index])

    metrics = {
        "five_fold_cv": {
            "r2_mean": float(np.mean([score.r2 for score in scores])),
            "r2_std": float(np.std([score.r2 for score in scores])),
            "mae_mean": float(np.mean([score.mae for score in scores])),
            "mae_std": float(np.std([score.mae for score in scores])),
        },
        "chronological_holdout": asdict(temporal),
    }
    return metrics, out_of_fold, holdout_index, holdout_prediction


def feature_group(feature_name: str) -> str:
    if feature_name.startswith("title_") or feature_name in {
        "has_number_in_title", "has_question_mark", "caps_ratio"
    }:
        return "Title packaging"
    if feature_name.startswith("tag_"):
        return "Tags"
    if feature_name.startswith("description_"):
        return "Description"
    if feature_name.startswith("publish_") or feature_name == "is_weekend":
        return "Publish timing"
    if feature_name.startswith("category_name_"):
        return "Category"
    return "Other"


def write_importance_reports(bundle: dict[str, object]) -> None:
    # Imported here so the deployed app (which never trains) does not need matplotlib.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    importances: list[pd.DataFrame] = []
    for target_name, model in bundle["models"].items():
        pipeline: Pipeline = model
        names = pipeline.named_steps["preprocessor"].get_feature_names_out()
        values = pipeline.named_steps["regressor"].feature_importances_
        frame = pd.DataFrame({"feature": names, "importance": values})
        frame["target"] = target_name
        frame["group"] = frame["feature"].map(feature_group)
        importances.append(frame)

    combined = pd.concat(importances, ignore_index=True)
    group_totals = combined.groupby(["target", "group"], as_index=False)["importance"].sum()
    group_totals.to_csv(GROUP_IMPORTANCE_PATH, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for axis, target_name, color in zip(
        axes, ["views_log", "engagement_rate"], ["#00BFA6", "#FF7043"]
    ):
        top = (
            combined.loc[combined["target"] == target_name]
            .nlargest(12, "importance")
            .sort_values("importance")
        )
        axis.barh(top["feature"], top["importance"], color=color)
        axis.set_title(f"Top pre-publication features — {target_name}")
        axis.set_xlabel("Random Forest importance")
        axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(IMPORTANCE_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_model_card(metrics: dict[str, object], row_count: int, calibration: dict[str, object]) -> None:
    views = metrics["views_log"]
    engagement = metrics["engagement_rate"]
    check = calibration["coverage_check"]
    MODEL_CARD_PATH.write_text(
        "# Advanced Model Card\n\n"
        "## Purpose\n\n"
        "Estimate relative performance among videos that already reached India’s Trending list. "
        "The app is a pre-publication decision aid, not a promise of views or a viral/non-viral classifier.\n\n"
        "## Training data\n\n"
        f"{row_count:,} unique India-trending video snapshots after de-duplication. "
        "Every input is available before publishing. Likes, dislikes, comments, views, video ID, "
        "and channel fields are excluded from model inputs.\n\n"
        "## Student-explainable additions\n\n"
        "The advanced version retains the original title, tag, category, description and timing fields, "
        "then adds transparent counts and ratios: punctuation, emoji, digit, urgency and how-to wording in "
        "the title; tag length and multiword-tag ratio; description links, hashtags and call-to-action words; "
        "and weekend/cyclical time fields. These are descriptive associations, not causal rules.\n\n"
        "## Validation\n\n"
        f"- Log views, 5-fold CV R²: {views['five_fold_cv']['r2_mean']:.3f} ± {views['five_fold_cv']['r2_std']:.3f}\n"
        f"- Engagement rate, 5-fold CV R²: {engagement['five_fold_cv']['r2_mean']:.3f} ± {engagement['five_fold_cv']['r2_std']:.3f}\n"
        f"- Log views, chronological holdout R²: {views['chronological_holdout']['r2']:.3f}\n"
        f"- Engagement rate, chronological holdout R²: {engagement['chronological_holdout']['r2']:.3f}\n\n"
        "## Honest uncertainty (split-conformal intervals)\n\n"
        f"Intervals are calibrated on out-of-fold errors so that about {calibration['coverage_target']:.0%} of true values fall inside. "
        f"Measured coverage: {check['views_out_of_fold']:.1%} (views) and {check['engagement_out_of_fold']:.1%} (engagement) out-of-fold; "
        f"on the later-in-time holdout {check['views_chronological_holdout']:.1%} and {check['engagement_chronological_holdout']:.1%}. "
        f"A views interval is the forecast times {calibration['views_multiplier_low']:.2f} to {calibration['views_multiplier_high']:.2f}.\n\n"
        "## Limits\n\n"
        "The source contains only videos that trended, so it cannot answer whether an arbitrary upload will trend. "
        "It also lacks thumbnails, channel history, audience retention and YouTube ranking signals. "
        "Feature importance is not proof that changing one field will cause the predicted outcome.\n",
        encoding="utf-8",
    )


def train_and_save() -> dict[str, object]:
    """Train both targets, save the inference bundle, and create assessment reports."""
    if not CLEAN_PATH.exists():
        raise FileNotFoundError(f"Missing {CLEAN_PATH}. Run src/clean.py first.")
    data = pd.read_csv(CLEAN_PATH)
    feature_table = build_feature_table(data)
    numeric_columns, categorical_columns = model_columns(feature_table)
    X = feature_table[numeric_columns + categorical_columns]
    timestamps = feature_table["publish_timestamp"]
    template = make_model(numeric_columns, categorical_columns)

    metrics: dict[str, object] = {}
    models: dict[str, Pipeline] = {}
    oof: dict[str, np.ndarray] = {}
    holdout: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    targets = {
        "views_log": np.log1p(feature_table["views"]),
        "engagement_rate": feature_table["engagement_rate"],
    }
    for target_name, target in targets.items():
        print(f"Evaluating {target_name} ...")
        metrics[target_name], oof[target_name], hold_index, hold_pred = evaluate_target(
            template, X, target, timestamps
        )
        holdout[target_name] = (hold_index, hold_pred)
        final_model = clone(template)
        final_model.fit(X, target)
        models[target_name] = final_model

    numeric_summary = {
        column: {
            "p05": float(feature_table[column].quantile(0.05)),
            "p50": float(feature_table[column].median()),
            "p95": float(feature_table[column].quantile(0.95)),
        }
        for column in numeric_columns
    }

    categories_series = feature_table[CATEGORY_COLUMN]
    calibration = artifacts.build_calibration(
        views_actual_log=targets["views_log"].to_numpy(),
        views_oof=oof["views_log"],
        engagement_actual=targets["engagement_rate"].to_numpy(),
        engagement_oof=oof["engagement_rate"],
        holdout_index=holdout["views_log"][0],
        views_holdout_pred=holdout["views_log"][1],
        engagement_holdout_pred=holdout["engagement_rate"][1],
    )
    reference = artifacts.build_reference(
        category=categories_series,
        views_actual=feature_table["views"].to_numpy(),
        engagement_actual=feature_table["engagement_rate"].to_numpy(),
        views_oof_log=oof["views_log"],
        engagement_oof=oof["engagement_rate"],
    )
    word_stats = artifacts.build_word_stats(
        data["title"], feature_table["views"].to_numpy(), feature_table["engagement_rate"].to_numpy(),
        data["channel_title"],
    )
    similarity = artifacts.build_similarity_index(
        data, categories_series, feature_table["engagement_rate"].to_numpy()
    )
    background = X.sample(n=min(120, len(X)), random_state=RANDOM_STATE).reset_index(drop=True)

    bundle: dict[str, object] = {
        "version": "ta4-explainable-v2",
        "models": models,
        "input_columns": numeric_columns + categorical_columns,
        "numeric_summary": numeric_summary,
        "categories": sorted(feature_table[CATEGORY_COLUMN].dropna().unique().tolist()),
        "training_rows": int(len(feature_table)),
        "metrics": metrics,
        "calibration": calibration,
        "reference": reference,
        "word_stats": word_stats,
        "background": background,
        "notes": "Targets: log1p(views) and engagement rate. Inputs are pre-publication metadata only.",
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, BUNDLE_PATH, compress=3)
    joblib.dump(similarity, SIMILARITY_PATH, compress=3)
    CALIBRATION_PATH.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_importance_reports(bundle)
    write_model_card(metrics, len(feature_table), calibration)
    print(json.dumps(metrics, indent=2))
    print(f"Saved inference bundle to {BUNDLE_PATH}")
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train", action="store_true", help="Train models and refresh the advanced reports."
    )
    arguments = parser.parse_args()
    if not arguments.train:
        parser.error("Pass --train to run the reproducible training workflow.")
    train_and_save()


if __name__ == "__main__":
    main()
