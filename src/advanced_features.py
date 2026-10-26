"""Build the advanced, creator-known feature table for model version 2."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from model_contract import FEATURE_VERSION, build_training_feature_frame

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "processed" / "clean.csv"
CATEGORY_PATH = ROOT / "data" / "IN_category_id.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "advanced_features.csv"


def load_data() -> tuple[pd.DataFrame, dict[str, str]]:
    if not CLEAN_PATH.exists():
        raise SystemExit(f"{CLEAN_PATH} not found. Run src/clean.py first.")
    if not CATEGORY_PATH.exists():
        raise SystemExit(f"{CATEGORY_PATH} not found.")
    with CATEGORY_PATH.open(encoding="utf-8") as handle:
        categories = json.load(handle)
    category_map = {
        str(item["id"]): item["snippet"]["title"] for item in categories["items"]
    }
    return pd.read_csv(CLEAN_PATH), category_map


def build_advanced_features(df: pd.DataFrame, category_map: dict[str, str]) -> pd.DataFrame:
    """Append outcomes and timestamp solely for later evaluation, never as model input."""
    features = build_training_feature_frame(df, category_map)
    features.insert(0, "video_id", df["video_id"].astype(str).to_numpy())
    features["published_at_utc"] = pd.to_datetime(df["publish_time"], utc=True).astype(str)
    features["views"] = pd.to_numeric(df["views"], errors="raise")
    features["engagement_rate"] = (
        pd.to_numeric(df["likes"], errors="raise")
        + pd.to_numeric(df["comment_count"], errors="raise")
    ) / features["views"]
    return features


def main() -> None:
    data, category_map = load_data()
    feature_table = build_advanced_features(data, category_map)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    feature_table.to_csv(OUTPUT_PATH, index=False)
    print(f"Feature version: {FEATURE_VERSION}")
    print(f"Saved {len(feature_table):,} rows and {len(feature_table.columns):,} columns to {OUTPUT_PATH}")
    print(feature_table.select_dtypes(include=["number"]).describe().round(3).to_string())


if __name__ == "__main__":
    main()
