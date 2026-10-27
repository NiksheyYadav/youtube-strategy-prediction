"""Channel-history features: what a creator's earlier videos say about the next one.

The same code builds these features for training (many channels at once) and for the live app (one connected or
uploaded channel), so the two can never drift apart.

Rule that prevents look-ahead: a video only counts as history for a new video if it was published *before* the new
video AND its views were already known at the moment the new video is published.  In the Kaggle trending data the
views of a video are known after its last trending day, so ``known_at`` is that day plus one.  For a creator who
connects their channel today, every earlier video is known, so ``known_at`` is simply the time of the export.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HISTORY_COLUMNS = [
    "prior_n",
    "prior_mean_logviews",
    "prior_median_logviews",
    "prior_last_logviews",
    "prior_max_logviews",
    "prior_std_logviews",
    "prior_median_engagement",
    "prior_days_since_last",
    "prior_missing",
]
MIN_USABLE_VIDEOS = 3  # below this the app keeps using the cold-start model (history would be too noisy)
MISSING_FILL = -1.0    # tree models need a number; ``prior_missing`` tells them it is a filler


def _empty_row() -> dict[str, float]:
    row = {name: MISSING_FILL for name in HISTORY_COLUMNS}
    row["prior_n"] = 0.0
    row["prior_missing"] = 1.0
    return row


def history_row(
    history: pd.DataFrame,
    publish_time: pd.Timestamp,
    *,
    recent: int | None = None,
) -> dict[str, float]:
    """History features for ONE new video published at ``publish_time``.

    ``history`` needs the columns ``publish_time`` (UTC), ``known_at`` (UTC), ``views`` and, optionally,
    ``engagement``.  ``recent`` keeps only the newest N usable videos (creators change over time).
    """
    if history is None or len(history) == 0:
        return _empty_row()
    publish_time = pd.Timestamp(publish_time)
    if publish_time.tzinfo is None:
        publish_time = publish_time.tz_localize("UTC")
    published = pd.to_datetime(history["publish_time"], utc=True)
    known = pd.to_datetime(history["known_at"], utc=True)
    usable = history[(published < publish_time) & (known <= publish_time)].copy()
    if usable.empty:
        return _empty_row()
    usable["publish_time"] = pd.to_datetime(usable["publish_time"], utc=True)
    usable = usable.sort_values("publish_time")
    if recent:
        usable = usable.tail(int(recent))
    log_views = np.log1p(usable["views"].astype(float).clip(lower=0).to_numpy())
    engagement = (
        usable["engagement"].astype(float).to_numpy() if "engagement" in usable else np.full(len(usable), np.nan)
    )
    engagement = engagement[np.isfinite(engagement)]
    return {
        "prior_n": float(len(usable)),
        "prior_mean_logviews": float(log_views.mean()),
        "prior_median_logviews": float(np.median(log_views)),
        "prior_last_logviews": float(log_views[-1]),
        "prior_max_logviews": float(log_views.max()),
        "prior_std_logviews": float(log_views.std()),
        "prior_median_engagement": float(np.median(engagement)) if len(engagement) else MISSING_FILL,
        "prior_days_since_last": float((publish_time - usable["publish_time"].iloc[-1]) / pd.Timedelta(days=1)),
        "prior_missing": 0.0,
    }


def add_history_features(
    frame: pd.DataFrame,
    *,
    channel: str = "channel_title",
    publish_time: str = "publish_time",
    known_at: str = "known_at",
    views: str = "views",
    engagement: str = "engagement",
    recent: int | None = None,
) -> pd.DataFrame:
    """History features for every row of ``frame`` (row order and index are preserved)."""
    published = pd.to_datetime(frame[publish_time], utc=True).to_numpy()
    known = pd.to_datetime(frame[known_at], utc=True).to_numpy()
    log_views = np.log1p(frame[views].astype(float).clip(lower=0).to_numpy())
    eng = frame[engagement].astype(float).to_numpy() if engagement in frame else np.full(len(frame), np.nan)
    out = np.tile(np.array([_empty_row()[name] for name in HISTORY_COLUMNS]), (len(frame), 1))
    column = {name: position for position, name in enumerate(HISTORY_COLUMNS)}

    for positions in frame.groupby(channel, sort=False).indices.values():
        positions = positions[np.argsort(published[positions], kind="stable")]
        for rank, target in enumerate(positions):
            earlier = positions[:rank]
            usable = earlier[(published[earlier] < published[target]) & (known[earlier] <= published[target])]
            if recent:
                usable = usable[-int(recent):]
            if len(usable) == 0:
                continue
            values = log_views[usable]
            reactions = eng[usable]
            reactions = reactions[np.isfinite(reactions)]
            row = out[target]
            row[column["prior_n"]] = len(usable)
            row[column["prior_mean_logviews"]] = values.mean()
            row[column["prior_median_logviews"]] = np.median(values)
            row[column["prior_last_logviews"]] = values[-1]
            row[column["prior_max_logviews"]] = values.max()
            row[column["prior_std_logviews"]] = values.std()
            row[column["prior_median_engagement"]] = np.median(reactions) if len(reactions) else MISSING_FILL
            row[column["prior_days_since_last"]] = (published[target] - published[usable[-1]]) / np.timedelta64(1, "D")
            row[column["prior_missing"]] = 0.0
    return pd.DataFrame(out, columns=HISTORY_COLUMNS, index=frame.index)
