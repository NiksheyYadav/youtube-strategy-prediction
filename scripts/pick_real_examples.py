"""Choose real videos from the dataset to use as the app's 'Try a real video' examples (instead of invented drafts).

    python scripts/pick_real_examples.py            # prints the candidates it would pick
    python scripts/pick_real_examples.py --write    # writes knowledge/real_examples.json

Rule (deterministic, no randomness): for each wanted category take the real video whose views are closest to that category's
median among videos with an English title, a description of 120-700 characters, at least 3 tags, no links in the description, ratings and comments switched
on, and a title of 25-80 characters.  Every field comes straight from the dataset; nothing is invented or edited except
shortening a long description.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.advanced_model import CLEAN_PATH, category_mapping, normalise_tags  # noqa: E402

OUT = ROOT / "knowledge" / "real_examples.json"
WANTED = ["Education", "Science & Technology", "Music", "Entertainment"]


def latin_share(text: str) -> float:
    letters = [c for c in str(text) if c.isalpha()]
    return sum(c.isascii() for c in letters) / len(letters) if letters else 1.0


def pick() -> list[dict[str, object]]:
    data = pd.read_csv(CLEAN_PATH)
    data["category_name"] = data["category_id"].astype(str).map(category_mapping()).fillna("Unknown")
    published = pd.to_datetime(data["publish_time"], utc=True) + pd.Timedelta(hours=5.5)  # IST, as everywhere in the project
    data["day"], data["hour"] = published.dt.dayofweek, published.dt.hour
    data["engagement"] = (data["likes"] + data["comment_count"]) / data["views"]
    data["tag_count"] = data["tags"].map(lambda t: 0 if t == "[none]" else len(normalise_tags(t).split("|")))
    description = data["description"].fillna("")
    ok = (
        data["title"].map(latin_share).ge(0.95) & data["title"].str.len().between(25, 80)
        & description.str.len().between(120, 700) & description.str.count("http").eq(0) & ~description.str.contains("www\.", regex=True)
        & data["tag_count"].ge(3)
        & ~data["ratings_disabled"].astype(str).str.lower().eq("true") & ~data["comments_disabled"].astype(str).str.lower().eq("true")
        & ~data["video_error_or_removed"].astype(str).str.lower().eq("true")
    )
    chosen = []
    for category in WANTED:
        pool = data[ok & data["category_name"].eq(category)]
        median = data.loc[data["category_name"].eq(category), "views"].median()
        row = pool.iloc[(pool["views"] - median).abs().argsort().iloc[0]]
        chosen.append({
            "video_id": row["video_id"], "channel": row["channel_title"], "title": row["title"], "category": category,
            "day": int(row["day"]), "hour": int(row["hour"]),
            "tags": ", ".join(t for t in normalise_tags(row["tags"]).split("|") if t),
            "description": str(row["description"]).strip(),
            "actual_views": int(row["views"]), "actual_engagement": float(row["engagement"]),
        })
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    chosen = pick()
    for item in chosen:
        print(f"[{item['category']}] {item['title']!r}  ({item['channel']}, {item['actual_views']:,} views, "
              f"{item['actual_engagement'] * 100:.2f}% engagement, day={item['day']} hour={item['hour']})")
        print(f"    tags: {item['tags'][:110]}")
        print(f"    description: {item['description'][:160].replace(chr(10), ' ')!r}")
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"about": "Real India-trending videos taken unchanged from the Kaggle dataset (CC0). They are part of the "
                                            "training data, so a forecast for them is not a fair test of the model.",
                                   "videos": chosen}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
