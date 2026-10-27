"""One call that turns a draft plus a creator's own history into a personalised forecast (or says why it cannot)."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from src.channel_history import SETTLE_DAYS, ChannelHistory, history_table
from src.history_features import history_row
from src.history_model import HistoryPrediction, predict_with_history
from src.inference import predict_video
from src.insights import Draft


@dataclass(frozen=True)
class PersonalForecast:
    prediction: HistoryPrediction | None
    reason: str                 # "" when there is a prediction, else "no_models" or "not_enough_history"
    history: dict[str, float]   # the history features that were used
    usable_videos: int          # earlier videos whose views had settled


def personal_forecast(
    bundle: dict[str, object],
    models: dict[str, object] | None,
    draft: Draft,
    history: ChannelHistory,
    *,
    as_of: pd.Timestamp | None = None,
) -> PersonalForecast:
    """Forecast ``draft`` for the creator whose earlier videos are in ``history``; ``as_of`` defaults to now."""
    cold = predict_video(
        bundle, title=draft.title, tags=draft.tags, description=draft.description,
        category_name=draft.category_name, day_of_week=draft.day_of_week, publish_hour=draft.publish_hour,
    )
    row = history_row(history_table(history), as_of or pd.Timestamp.now(tz="UTC"))
    usable = int(row["prior_n"])
    if models is None:
        return PersonalForecast(None, "no_models", row, usable)
    prediction = predict_with_history(models, cold.feature_row, row)
    if prediction is None:
        return PersonalForecast(None, "not_enough_history", row, usable)
    if prediction.engagement_source == "unavailable":
        # the creator's file has no likes or comments, so engagement comes from the trending-video model instead
        prediction = replace(
            prediction, engagement_rate=cold.engagement_rate, engagement_ci_low=cold.engagement_ci_low,
            engagement_ci_high=cold.engagement_ci_high, engagement_source="trending",
        )
    return PersonalForecast(prediction, "", row, usable)


# --------------------------------------------------------------------------- #
# Patterns in the creator's own history (observations for the AI Coach, never causes)
# --------------------------------------------------------------------------- #
OWN_PATTERN_MIN_GROUP = 4     # each side of a comparison needs this many videos
OWN_PATTERN_MIN_RATIO = 1.25  # and the medians must differ clearly (25%) before it is worth mentioning


def own_patterns(history: ChannelHistory, *, min_group: int = OWN_PATTERN_MIN_GROUP, limit: int = 2) -> list[dict[str, object]]:
    """Clear differences between groups of the creator's own settled videos (title with a number, 'how to', question, weekend)."""
    videos = history.videos[history.videos["publish_time"] <= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=SETTLE_DAYS)]
    if len(videos) < 2 * min_group:
        return []
    title = videos["title"].str.lower()
    published = videos["publish_time"] + (pd.Timedelta(hours=5.5) if history.hour_known else pd.Timedelta(0))
    flags = {
        "a number in the title": title.str.contains(r"\d", regex=True),
        "a title that starts with 'how'": title.str.startswith("how"),
        "a question in the title": title.str.contains(r"\?", regex=True),
        "a weekend publish day": published.dt.dayofweek >= 5,
    }
    found = []
    for label, mask in flags.items():
        with_flag, without = videos.loc[mask, "views"], videos.loc[~mask, "views"]
        if len(with_flag) < min_group or len(without) < min_group:
            continue
        median_with, median_without = float(with_flag.median()), float(without.median())
        if median_with <= 0 or median_without <= 0:
            continue
        ratio = median_with / median_without
        if ratio >= OWN_PATTERN_MIN_RATIO or ratio <= 1 / OWN_PATTERN_MIN_RATIO:
            found.append({"label": label, "n_with": int(len(with_flag)), "n_without": int(len(without)),
                          "median_with": median_with, "median_without": median_without, "ratio": ratio})
    found.sort(key=lambda item: abs(np.log(item["ratio"])) * np.sqrt(min(item["n_with"], item["n_without"])), reverse=True)
    return found[:limit]
