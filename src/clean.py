"""Stage 1: load raw IN trending-video data, dedupe, drop bad rows, parse dates."""

import sys
from pathlib import Path

import pandas as pd

RAW_PATH = Path("data/INvideos.csv")
OUT_PATH = Path("data/processed/clean.csv")

REQUIRED_COLUMNS = [
    "video_id",
    "title",
    "channel_title",
    "category_id",
    "publish_time",
    "tags",
    "views",
    "likes",
    "dislikes",
    "comment_count",
]


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(
            f"Data file not found at {path.resolve()}.\n"
            "Download the Kaggle 'Trending YouTube Video Statistics' IN CSV "
            "and place it there before running this script."
        )
    return pd.read_csv(path)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    df["trending_date"] = pd.to_datetime(df["trending_date"], format="%y.%d.%m")
    df["publish_time"] = pd.to_datetime(df["publish_time"])

    df = df.sort_values("trending_date").drop_duplicates(subset="video_id", keep="last")

    df = df.dropna(subset=REQUIRED_COLUMNS)

    after = len(df)
    print(f"Rows before cleaning: {before}")
    print(f"Rows after cleaning:  {after}")
    return df


def main() -> None:
    df = load(RAW_PATH)
    cleaned = clean(df)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Saved cleaned data to {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
