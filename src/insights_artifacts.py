"""Build-time helpers that turn the training data into small, shippable artifacts.

Everything here runs once during training.  The Streamlit app only loads the
results, so the deployed service never needs the raw Kaggle files.

Artifacts
---------
* conformal calibration  - honest prediction intervals with a measured coverage
* reference distributions - where a forecast sits among trending videos
* keyword statistics      - which title words co-occur with higher/lower views
* similarity index        - TF-IDF index used to find similar trending videos
"""

from __future__ import annotations

import math
import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

COVERAGE = 0.80
ENGAGEMENT_EPS = 0.004
MIN_GROUP_SIZE = 30
MIN_WORD_VIDEOS = 25
MIN_WORD_CHANNELS = 25  # a word used by only a few channels is a brand or catchphrase, not a strategy signal

STOPWORDS = frozenset(
    """a about after all also am an and any are as at be been being but by can did do does for from
    get got had has have he her here him his how i if in into is it its just me more most my new
    no not now of off on one only or our out over she so some than that the their them then there
    these they this to too up us very was we were what when where which who why will with you your
    video videos official full hd""".split()
)
MIN_CATEGORY_CALIBRATION = 120  # a category needs this many out-of-fold errors before it gets its own interval width


def word_tokens(text: object) -> list[str]:
    """Words in ANY script. Letters, combining marks (Hindi/Tamil vowel signs) and digits form a word; an apostrophe stays
    inside a word.  (The old splitter only knew A-Z, so a Hindi title counted as zero words.)"""
    tokens: list[str] = []
    current: list[str] = []
    for character in str(text).lower():
        if unicodedata.category(character)[0] in "LMN" or (character == "'" and current):
            current.append(character)
        elif current:
            tokens.append("".join(current).strip("'"))
            current = []
    if current:
        tokens.append("".join(current).strip("'"))
    return [token for token in tokens if token]


def _is_wordlike(token: str) -> bool:
    return len(token) >= 3 and not any(unicodedata.category(character) == "Nd" for character in token)


# --------------------------------------------------------------------------- #
# Split-conformal prediction intervals
# --------------------------------------------------------------------------- #
def conformal_quantile(scores: np.ndarray, coverage: float = COVERAGE) -> float:
    """Finite-sample-corrected quantile used by split conformal prediction."""
    scores = np.sort(np.asarray(scores, dtype=float))
    count = len(scores)
    rank = min(math.ceil((count + 1) * coverage), count)
    return float(scores[rank - 1])


def views_scores(actual_log: np.ndarray, predicted_log: np.ndarray) -> np.ndarray:
    return np.abs(np.asarray(actual_log) - np.asarray(predicted_log))


def engagement_scores(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """Locally weighted score: error relative to the size of the prediction."""
    predicted = np.asarray(predicted, dtype=float)
    return np.abs(np.asarray(actual) - predicted) / np.maximum(predicted, ENGAGEMENT_EPS)


def views_interval(predicted_log: float, q: float) -> tuple[float, float]:
    return (
        max(0.0, float(np.expm1(predicted_log - q))),
        max(0.0, float(np.expm1(predicted_log + q))),
    )


def engagement_interval(predicted: float, q: float) -> tuple[float, float]:
    scale = max(float(predicted), ENGAGEMENT_EPS)
    return max(0.0, float(predicted) - q * scale), float(predicted) + q * scale


def empirical_coverage(actual: np.ndarray, low: np.ndarray, high: np.ndarray) -> float:
    actual, low, high = (np.asarray(value, dtype=float) for value in (actual, low, high))
    return float(np.mean((actual >= low) & (actual <= high)))


def build_calibration(
    views_actual_log: np.ndarray,
    views_oof: np.ndarray,
    engagement_actual: np.ndarray,
    engagement_oof: np.ndarray,
    holdout_index: np.ndarray,
    views_holdout_pred: np.ndarray,
    engagement_holdout_pred: np.ndarray,
    *,
    engagement_holdout_index: np.ndarray | None = None,
    categories: np.ndarray | None = None,
) -> dict[str, object]:
    """Calibrate on out-of-fold errors, then test on the later-in-time holdout.

    Engagement values may be NaN (not measurable for that video); those rows are ignored.  With ``categories``, every category
    that has enough errors also gets its OWN interval width: one global width is right on average but wrong for some
    categories (before this change an "80% interval" held only 50% of the time for Gaming and 96% for Shows).
    """
    engagement_actual = np.asarray(engagement_actual, dtype=float)
    engagement_oof = np.asarray(engagement_oof, dtype=float)
    measurable = np.isfinite(engagement_actual) & np.isfinite(engagement_oof)
    q_views = conformal_quantile(views_scores(views_actual_log, views_oof))
    engagement_oof = np.maximum(engagement_oof, 0.0)
    q_engagement = conformal_quantile(engagement_scores(engagement_actual[measurable], engagement_oof[measurable]))

    # Coverage on the random out-of-fold predictions (should be close to 80 %).
    oof_views_cover = empirical_coverage(views_actual_log, views_oof - q_views, views_oof + q_views)
    scale = np.maximum(engagement_oof[measurable], ENGAGEMENT_EPS)
    oof_eng_cover = empirical_coverage(
        engagement_actual[measurable], engagement_oof[measurable] - q_engagement * scale, engagement_oof[measurable] + q_engagement * scale
    )

    # Honest test: later uploads the calibration never saw.
    hold_views_cover = empirical_coverage(
        views_actual_log[holdout_index], views_holdout_pred - q_views, views_holdout_pred + q_views
    )
    engagement_hold = np.asarray(holdout_index if engagement_holdout_index is None else engagement_holdout_index)
    hold_pred_eng = np.maximum(np.asarray(engagement_holdout_pred, dtype=float), 0.0)
    hold_ok = np.isfinite(engagement_actual[engagement_hold])
    hold_scale = np.maximum(hold_pred_eng[hold_ok], ENGAGEMENT_EPS)
    hold_eng_cover = empirical_coverage(
        engagement_actual[engagement_hold][hold_ok],
        hold_pred_eng[hold_ok] - q_engagement * hold_scale,
        hold_pred_eng[hold_ok] + q_engagement * hold_scale,
    )

    q_views_by_category: dict[str, float] = {}
    q_engagement_by_category: dict[str, float] = {}
    category_check: dict[str, dict[str, float]] = {}
    if categories is not None:
        names = np.asarray(categories)
        view_errors = views_scores(views_actual_log, views_oof)
        engagement_errors = np.full(len(names), np.nan)
        engagement_errors[measurable] = engagement_scores(engagement_actual[measurable], engagement_oof[measurable])
        for name in sorted(set(names.tolist())):
            in_category = names == name
            if in_category.sum() >= MIN_CATEGORY_CALIBRATION:
                q_views_by_category[str(name)] = conformal_quantile(view_errors[in_category])
            if (in_category & measurable).sum() >= MIN_CATEGORY_CALIBRATION:
                q_engagement_by_category[str(name)] = conformal_quantile(engagement_errors[in_category & measurable])
        # later uploads, category by category: the single global width versus the category's own width
        hold_names = names[holdout_index]
        hold_actual = np.asarray(views_actual_log)[holdout_index]
        for name in sorted(set(hold_names.tolist())):
            rows = hold_names == name
            if rows.sum() < 25:
                continue
            own = q_views_by_category.get(str(name), q_views)
            category_check[str(name)] = {
                "n_later_videos": int(rows.sum()),
                "global_width_coverage": empirical_coverage(hold_actual[rows], views_holdout_pred[rows] - q_views, views_holdout_pred[rows] + q_views),
                "category_width_coverage": empirical_coverage(hold_actual[rows], views_holdout_pred[rows] - own, views_holdout_pred[rows] + own),
            }
    return {
        "coverage_target": COVERAGE,
        "views_log_q": q_views,
        "engagement_q": q_engagement,
        "views_log_q_by_category": q_views_by_category,
        "engagement_q_by_category": q_engagement_by_category,
        "views_multiplier_low": float(np.exp(-q_views)),
        "views_multiplier_high": float(np.exp(q_views)),
        "coverage_check": {
            "views_out_of_fold": oof_views_cover,
            "engagement_out_of_fold": oof_eng_cover,
            "views_chronological_holdout": hold_views_cover,
            "engagement_chronological_holdout": hold_eng_cover,
            "views_later_videos_by_category": category_check,
        },
    }


# --------------------------------------------------------------------------- #
# Reference distributions
# --------------------------------------------------------------------------- #
def build_reference(
    category: pd.Series,
    views_actual: np.ndarray,
    engagement_actual: np.ndarray,
    views_oof_log: np.ndarray,
    engagement_oof: np.ndarray,
) -> dict[str, object]:
    """Sorted out-of-fold forecasts, so a new forecast is compared like with like."""
    frame = pd.DataFrame(
        {
            "category": category.to_numpy(),
            "views": views_actual,
            "engagement": engagement_actual,
            "views_oof_log": views_oof_log,
            "engagement_oof": np.maximum(engagement_oof, 0.0),
        }
    )
    per_category: dict[str, dict[str, object]] = {}
    for name, group in frame.groupby("category"):
        if len(group) < MIN_GROUP_SIZE:
            continue
        per_category[str(name)] = {
            "n": int(len(group)),
            "median_views": float(group["views"].median()),
            "median_engagement": float(group["engagement"].median()),
            "views_oof_log_sorted": np.sort(group["views_oof_log"].to_numpy()),
            "engagement_oof_sorted": np.sort(group["engagement_oof"].dropna().to_numpy()),
        }
    return {
        "n": int(len(frame)),
        "median_views": float(frame["views"].median()),
        "median_engagement": float(frame["engagement"].median()),
        "views_oof_log_sorted": np.sort(frame["views_oof_log"].to_numpy()),
        "engagement_oof_sorted": np.sort(frame["engagement_oof"].dropna().to_numpy()),
        "categories": per_category,
    }


# --------------------------------------------------------------------------- #
# Keyword statistics
# --------------------------------------------------------------------------- #
def title_words(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for word in word_tokens(text):
        if _is_wordlike(word) and word not in STOPWORDS:
            seen[word] = None
    return list(seen)


def build_word_stats(
    titles: pd.Series, views: np.ndarray, engagement: np.ndarray, channels: pd.Series
) -> dict[str, dict[str, float]]:
    """Median views / engagement of trending videos whose title contains each word.

    Words must appear in at least MIN_WORD_VIDEOS videos from at least MIN_WORD_CHANNELS
    different channels, which removes channel names and one-creator catchphrases.
    """
    rows = [
        (index, word)
        for index, title in enumerate(titles.fillna("").tolist())
        for word in title_words(title)
    ]
    exploded = pd.DataFrame(rows, columns=["row", "word"])
    exploded["views"] = np.asarray(views)[exploded["row"].to_numpy()]
    exploded["engagement"] = np.asarray(engagement)[exploded["row"].to_numpy()]
    exploded["channel"] = channels.fillna("").to_numpy()[exploded["row"].to_numpy()]
    grouped = exploded.groupby("word").agg(
        n=("row", "size"),
        n_channels=("channel", "nunique"),
        median_views=("views", "median"),
        median_engagement=("engagement", "median"),
    )
    grouped = grouped[(grouped["n"] >= MIN_WORD_VIDEOS) & (grouped["n_channels"] >= MIN_WORD_CHANNELS)]
    overall_views = float(np.median(views))
    overall_engagement = float(np.nanmedian(engagement))
    return {
        word: {
            "n": int(row.n),
            "n_channels": int(row.n_channels),
            "median_views": float(row.median_views),
            "median_engagement": float(row.median_engagement),
            "views_lift": float(row.median_views / overall_views),
            "engagement_lift": float(row.median_engagement / overall_engagement),
        }
        for word, row in grouped.iterrows()
    }


# --------------------------------------------------------------------------- #
# Similarity index
# --------------------------------------------------------------------------- #
def similarity_text(title: str, tags: str) -> str:
    tag_text = " ".join(
        part.strip().strip('"') for part in str(tags).split("|")[:15] if part.strip()
    )
    tag_text = "" if tag_text.lower() == "[none]" else tag_text
    return f"{title} {tag_text}".strip()


def build_similarity_index(
    data: pd.DataFrame, category_names: pd.Series, engagement: np.ndarray
) -> dict[str, object]:
    texts = [
        similarity_text(title, tags)
        for title, tags in zip(data["title"].fillna(""), data["tags"].fillna("[none]"))
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        tokenizer=word_tokens,
        token_pattern=None,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=40_000,
        sublinear_tf=True,
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(texts)
    return {
        "vectorizer": vectorizer,
        "matrix": matrix.tocsr(),
        "video_id": data["video_id"].astype(str).to_numpy(),
        "title": data["title"].fillna("").to_numpy(),
        "category": category_names.to_numpy(),
        "views": data["views"].astype(float).to_numpy(),
        "engagement": np.asarray(engagement, dtype=float),
    }
