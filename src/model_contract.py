"""Reusable, leakage-safe feature contract for the advanced prediction model.

The training scripts and Streamlit app both call this module.  Keeping the
feature engineering in one place prevents a common deployment error: creating
a different set or order of columns for a live prediction than the model saw
during training.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

FEATURE_VERSION = "2.0"

TOKEN_RE = re.compile(r"\b[^\W_]+\b", flags=re.UNICODE)
URL_RE = re.compile(r"(?:https?://|www\.)\S+", flags=re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<!\w)#\w+", flags=re.UNICODE)
CALL_TO_ACTION_RE = re.compile(
    r"\b(?:subscribe|like|comment|share|follow|turn on notifications|watch now)\b",
    flags=re.IGNORECASE,
)

RAW_MODEL_COLUMNS = [
    "category_name",
    "publish_day_of_week",
    "publish_hour",
    "title_length",
    "title_word_count",
    "title_avg_word_length",
    "title_lexical_diversity",
    "title_digit_count",
    "title_punctuation_count",
    "title_exclamation_count",
    "title_has_question_mark",
    "title_has_number",
    "title_caps_ratio",
    "title_uppercase_word_count",
    "title_has_brackets",
    "title_has_emoji",
    "tag_count",
    "tag_unique_count",
    "tag_avg_length",
    "tag_character_count",
    "description_length",
    "description_word_count",
    "description_avg_word_length",
    "description_url_count",
    "description_has_hashtag",
    "description_has_call_to_action",
    "description_reading_minutes",
    "publish_hour_sin",
    "publish_hour_cos",
    "publish_day_sin",
    "publish_day_cos",
]

FEATURE_LABELS = {
    "title_length": "Title length",
    "title_word_count": "Title word count",
    "title_avg_word_length": "Average title word length",
    "title_lexical_diversity": "Title lexical diversity",
    "title_digit_count": "Digits in title",
    "title_punctuation_count": "Title punctuation count",
    "title_exclamation_count": "Exclamation marks in title",
    "title_has_question_mark": "Question mark in title",
    "title_has_number": "Number in title",
    "title_caps_ratio": "Capital-letter ratio",
    "title_uppercase_word_count": "All-caps title words",
    "title_has_brackets": "Bracketed text in title",
    "title_has_emoji": "Emoji in title",
    "tag_count": "Tag count",
    "tag_unique_count": "Unique tag count",
    "tag_avg_length": "Average tag length",
    "tag_character_count": "Tag text length",
    "description_length": "Description length",
    "description_word_count": "Description word count",
    "description_avg_word_length": "Average description word length",
    "description_url_count": "Links in description",
    "description_has_hashtag": "Hashtag in description",
    "description_has_call_to_action": "Call to action in description",
    "description_reading_minutes": "Estimated description reading time",
    "publish_day_of_week": "Publish day",
    "publish_hour": "Publish hour",
    "publish_hour_sin": "Publish-hour cycle",
    "publish_hour_cos": "Publish-hour cycle",
    "publish_day_sin": "Publish-day cycle",
    "publish_day_cos": "Publish-day cycle",
}


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text))


def _is_emoji(character: str) -> bool:
    """A dependency-free, intentionally conservative emoji detector."""
    codepoint = ord(character)
    return (
        0x1F300 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or unicodedata.category(character) == "So"
    )


def normalise_tags(tags: str | Iterable[str] | None) -> list[str]:
    """Accept Kaggle pipe-separated tags and normal comma-separated app input."""
    if tags is None or (isinstance(tags, float) and math.isnan(tags)):
        return []
    if isinstance(tags, str):
        if tags.strip().lower() in {"", "[none]", "none"}:
            return []
        parts = re.split(r"[|,\n]", tags)
    else:
        parts = list(tags)
    return [str(part).strip() for part in parts if str(part).strip()]


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def make_input_row(
    title: str,
    category_name: str,
    tags: str | Iterable[str] | None,
    description: str,
    publish_day_of_week: int,
    publish_hour: int,
) -> dict[str, float | int | str]:
    """Turn only creator-known metadata into one leakage-safe model row."""
    if not 0 <= int(publish_day_of_week) <= 6:
        raise ValueError("publish_day_of_week must be an integer from 0 (Monday) to 6 (Sunday).")
    if not 0 <= int(publish_hour) <= 23:
        raise ValueError("publish_hour must be an integer from 0 to 23.")

    title = str(title or "").strip()
    description = str(description or "").strip()
    title_words = _tokens(title)
    description_words = _tokens(description)
    parsed_tags = normalise_tags(tags)
    title_letters = [character for character in title if character.isalpha()]
    punctuation_count = sum(
        1 for character in title if unicodedata.category(character).startswith("P")
    )
    uppercase_words = sum(
        1 for word in title_words if len(word) > 1 and word.isupper()
    )

    hour_angle = 2 * math.pi * int(publish_hour) / 24
    day_angle = 2 * math.pi * int(publish_day_of_week) / 7
    return {
        "category_name": str(category_name or "Unknown").strip() or "Unknown",
        "publish_day_of_week": int(publish_day_of_week),
        "publish_hour": int(publish_hour),
        "title_length": len(title),
        "title_word_count": len(title_words),
        "title_avg_word_length": _safe_ratio(sum(map(len, title_words)), len(title_words)),
        "title_lexical_diversity": _safe_ratio(
            len({word.casefold() for word in title_words}), len(title_words)
        ),
        "title_digit_count": sum(character.isdigit() for character in title),
        "title_punctuation_count": punctuation_count,
        "title_exclamation_count": title.count("!"),
        "title_has_question_mark": int("?" in title),
        "title_has_number": int(any(character.isdigit() for character in title)),
        "title_caps_ratio": _safe_ratio(
            sum(character.isupper() for character in title_letters), len(title_letters)
        ),
        "title_uppercase_word_count": uppercase_words,
        "title_has_brackets": int(any(character in "()[]{}" for character in title)),
        "title_has_emoji": int(any(_is_emoji(character) for character in title)),
        "tag_count": len(parsed_tags),
        "tag_unique_count": len({tag.casefold() for tag in parsed_tags}),
        "tag_avg_length": _safe_ratio(sum(map(len, parsed_tags)), len(parsed_tags)),
        "tag_character_count": sum(map(len, parsed_tags)),
        "description_length": len(description),
        "description_word_count": len(description_words),
        "description_avg_word_length": _safe_ratio(
            sum(map(len, description_words)), len(description_words)
        ),
        "description_url_count": len(URL_RE.findall(description)),
        "description_has_hashtag": int(bool(HASHTAG_RE.search(description))),
        "description_has_call_to_action": int(bool(CALL_TO_ACTION_RE.search(description))),
        "description_reading_minutes": round(len(description_words) / 200, 3),
        "publish_hour_sin": round(math.sin(hour_angle), 8),
        "publish_hour_cos": round(math.cos(hour_angle), 8),
        "publish_day_sin": round(math.sin(day_angle), 8),
        "publish_day_cos": round(math.cos(day_angle), 8),
    }


def build_training_feature_frame(
    df: pd.DataFrame, category_map: dict[str, str]
) -> pd.DataFrame:
    """Create advanced features from raw cleaned records without target leakage."""
    category_names = df["category_id"].astype(str).map(category_map).fillna("Unknown")
    publish_times = pd.to_datetime(df["publish_time"], utc=True)
    ist_times = publish_times + pd.Timedelta(hours=5.5)

    records = [
        make_input_row(
            title=title,
            category_name=category_name,
            tags=tags,
            description=description,
            publish_day_of_week=published_at.dayofweek,
            publish_hour=published_at.hour,
        )
        for title, category_name, tags, description, published_at in zip(
            df["title"].fillna(""),
            category_names,
            df["tags"].fillna("[none]"),
            df["description"].fillna(""),
            ist_times,
        )
    ]
    return pd.DataFrame.from_records(records, columns=RAW_MODEL_COLUMNS)


def build_training_design_matrix(raw_features: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode category with a stable, inspectable training design matrix."""
    missing = set(RAW_MODEL_COLUMNS) - set(raw_features.columns)
    if missing:
        raise ValueError(f"Missing raw feature columns: {sorted(missing)}")
    matrix = raw_features[RAW_MODEL_COLUMNS].copy()
    matrix = pd.get_dummies(matrix, columns=["category_name"], drop_first=True, dtype=int)
    return matrix.astype(float)


def build_inference_design_matrix(
    raw_rows: pd.DataFrame | Sequence[dict[str, float | int | str]],
    expected_columns: Sequence[str],
) -> pd.DataFrame:
    """Align live app input to the exact columns stored at training time."""
    frame = pd.DataFrame(raw_rows).copy()
    missing = set(RAW_MODEL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing raw feature columns: {sorted(missing)}")

    category_names = frame["category_name"].fillna("Unknown").astype(str)
    matrix = frame[RAW_MODEL_COLUMNS].drop(columns="category_name").copy()
    for category in category_names.unique():
        column = f"category_name_{category}"
        if column in expected_columns:
            matrix[column] = (category_names == category).astype(int)
    return matrix.reindex(columns=list(expected_columns), fill_value=0).astype(float)


def friendly_feature_name(feature_name: str) -> str:
    if feature_name.startswith("category_name_"):
        return f"Category: {feature_name.removeprefix('category_name_')}"
    return FEATURE_LABELS.get(feature_name, feature_name.replace("_", " ").title())
