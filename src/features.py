"""Stage 2: build the pre-publish feature table from cleaned IN trending video data."""

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

CLEAN_PATH = Path("data/processed/clean.csv")
CATEGORY_PATH = Path("data/IN_category_id.json")
OUT_PATH = Path("data/processed/features.csv")
CORR_PLOT_PATH = Path("reports/eda_corr.png")

IST_OFFSET_HOURS = 5.5


def load(clean_path: Path, category_path: Path) -> tuple[pd.DataFrame, dict]:
    if not clean_path.exists():
        raise SystemExit(f"{clean_path} not found — run src/clean.py first.")
    if not category_path.exists():
        raise SystemExit(f"{category_path} not found.")

    df = pd.read_csv(clean_path)

    with open(category_path, encoding="utf-8") as f:
        category_json = json.load(f)
    category_map = {
        str(item["id"]): item["snippet"]["title"] for item in category_json["items"]
    }
    return df, category_map


def tag_count(tags: str) -> int:
    if pd.isna(tags) or tags == "[none]":
        return 0
    return len(tags.split("|"))


def caps_ratio(title: str) -> float:
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return 0.0
    caps = sum(1 for c in letters if c.isupper())
    return caps / len(letters)


def build_features(df: pd.DataFrame, category_map: dict) -> pd.DataFrame:
    out = pd.DataFrame()
    out["video_id"] = df["video_id"]

    out["category_id"] = df["category_id"]
    out["category_name"] = (
        df["category_id"].astype(str).map(category_map).fillna("Unknown")
    )

    publish_time_ist = pd.to_datetime(df["publish_time"], utc=True) + pd.Timedelta(
        hours=IST_OFFSET_HOURS
    )
    out["publish_day_of_week"] = publish_time_ist.dt.dayofweek
    out["publish_hour"] = publish_time_ist.dt.hour

    title = df["title"].fillna("")
    out["title_length"] = title.str.len()
    out["title_word_count"] = title.str.split().str.len()
    out["has_number_in_title"] = title.str.contains(r"\d", regex=True)
    out["has_question_mark"] = title.str.contains("?", regex=False)
    out["caps_ratio"] = title.apply(caps_ratio)

    out["tag_count"] = df["tags"].apply(tag_count)

    out["description_length"] = df["description"].fillna("").str.len()

    out["views"] = df["views"]
    out["engagement_rate"] = (df["likes"] + df["comment_count"]) / df["views"]

    return out


def main() -> None:
    df, category_map = load(CLEAN_PATH, CATEGORY_PATH)
    features = build_features(df, category_map)

    numeric_cols = features.select_dtypes(include=["number", "bool"]).columns
    print(features[numeric_cols].describe())

    CORR_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    corr = features[numeric_cols].astype(float).corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
    plt.tight_layout()
    plt.savefig(CORR_PLOT_PATH)
    plt.close()
    print(f"Saved correlation heatmap to {CORR_PLOT_PATH.resolve()}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUT_PATH, index=False)
    print(f"Saved feature table ({len(features)} rows) to {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
