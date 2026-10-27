"""Real data for the tests: real India-trending videos from the Kaggle dataset (nothing here is invented).

The dataset is not stored in git (it is large and not ours to redistribute); tests that need it are skipped, with a clear
reason, on a machine where ``python src/clean.py`` has not been run.  On a developer machine they all run.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.advanced_model import CLEAN_PATH
from src.channel_history import ChannelHistory, clean_videos

HAVE_DATA = CLEAN_PATH.exists()
requires_data = pytest.mark.skipif(not HAVE_DATA, reason="needs data/processed/clean.csv (run: python src/clean.py)")


def _clean() -> pd.DataFrame:
    return pd.read_csv(CLEAN_PATH)


def real_channel(min_videos: int = 20, rank: int = 0, with_reactions: bool = True) -> ChannelHistory:
    """The real channel with the ``rank``-th most trending videos, as a creator-history table (title, date, views, likes, comments)."""
    data = _clean()
    counts = data["channel_title"].value_counts()
    ordered = counts[counts >= min_videos].reset_index().sort_values(["count", "channel_title"], ascending=[False, True])
    name = ordered["channel_title"].iloc[rank]
    rows = data[data["channel_title"] == name]
    frame = pd.DataFrame({"video_id": rows["video_id"], "title": rows["title"], "publish_time": rows["publish_time"], "views": rows["views"]})
    if with_reactions:
        frame["likes"], frame["comments"] = rows["likes"], rows["comment_count"]
    return clean_videos(frame, source="api")


def real_training_subset(n_channels: int = 160, min_videos: int = 8, seed: int = 0) -> pd.DataFrame:
    """Whole real channels (every one of their trending videos), so history features are meaningful; small enough to train quickly."""
    data = _clean()
    counts = data["channel_title"].value_counts()
    eligible = sorted(counts[counts >= min_videos].index)
    rng = np.random.default_rng(seed)
    chosen = set(rng.choice(eligible, size=min(n_channels, len(eligible)), replace=False))
    return data[data["channel_title"].isin(chosen)].reset_index(drop=True)
