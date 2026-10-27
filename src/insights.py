"""Explainable analytics built on top of the trained model.

Each public function answers one plain question a creator (or a professor) might ask:

* ``explain_groups``      Why did the model forecast this?          (exact group Shapley values)
* ``time_grid``           When should I publish?                    (168 day x hour what-ifs)
* ``suggest_edits``       What edits does the model associate with more views?
* ``category_what_if``    How would the model see the same draft in another category?
* ``keyword_signals``     Which title words co-occur with higher / lower views?
* ``similar_videos``      Which trending videos look like mine, and what did they get?
* ``forecast_percentile`` Where does the forecast sit among trending videos?

All of them only use pre-publication inputs, and every one re-uses the same feature
code and trained model as the main forecast, so nothing can drift out of sync.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.advanced_model import (
    CTA_WORDS,
    _tokens,
    build_demo_features,
    normalise_tags,
)
from src.inference import predict_frame
from src.insights_artifacts import STOPWORDS, similarity_text, title_words

ROOT = Path(__file__).resolve().parents[1]
SIMILARITY_PATH = ROOT / "models" / "similarity_index.joblib"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
GROUPS = ["Title packaging", "Tags", "Description", "Publish timing", "Category"]
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v="


@dataclass(frozen=True)
class Draft:
    """A proposed video: only things a creator knows before uploading."""

    title: str
    tags: str
    description: str
    category_name: str
    day_of_week: int
    publish_hour: int

    def features(self) -> pd.DataFrame:
        return build_demo_features(
            title=self.title,
            tags=self.tags,
            description=self.description,
            category_name=self.category_name,
            day_of_week=self.day_of_week,
            publish_hour=self.publish_hour,
        )

    def with_changes(self, **changes: object) -> "Draft":
        return replace(self, **changes)


def input_group(column: str) -> str:
    """Map a model input column to one of five strategy groups."""
    if column == "category_name":
        return "Category"
    if column.startswith("tag_"):
        return "Tags"
    if column.startswith("description_"):
        return "Description"
    if column.startswith("publish_") or column == "is_weekend":
        return "Publish timing"
    return "Title packaging"


def _predict_drafts(bundle: dict[str, object], drafts: list[Draft]) -> tuple[np.ndarray, np.ndarray]:
    frame = pd.concat([draft.features() for draft in drafts], ignore_index=True)
    return predict_frame(bundle, frame)


# --------------------------------------------------------------------------- #
# 1. Why this forecast?  Exact Shapley values over five feature groups
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Explanation:
    table: pd.DataFrame
    baseline_views: float
    forecast_views: float
    baseline_engagement: float
    forecast_engagement: float


def explain_groups(bundle: dict[str, object], draft: Draft, n_background: int = 80) -> Explanation:
    """Split the forecast into one contribution per strategy group.

    Shapley idea in one sentence: reveal the five groups of the draft one at a time
    in every possible order, starting from a typical trending video, and average how
    much each group moves the forecast when it is revealed.  With only five groups
    the average can be computed exactly (2^5 = 32 coalitions), so no approximation
    or extra library is needed.  The contributions always add up to
    (forecast - baseline).
    """
    columns = list(bundle["input_columns"])
    draft_row = draft.features().reindex(columns=columns).iloc[0]
    background = bundle["background"][columns].head(n_background).reset_index(drop=True)
    group_columns = {group: [c for c in columns if input_group(c) == group] for group in GROUPS}
    n_groups = len(GROUPS)
    n_masks = 2**n_groups

    frames = []
    for mask in range(n_masks):
        frame = background.copy()
        for position, group in enumerate(GROUPS):
            if mask >> position & 1:
                for column in group_columns[group]:
                    frame[column] = draft_row[column]
        frames.append(frame)
    views_log, engagement = predict_frame(bundle, pd.concat(frames, ignore_index=True))
    value_views = views_log.reshape(n_masks, -1).mean(axis=1)
    value_engagement = engagement.reshape(n_masks, -1).mean(axis=1)

    def shapley(values: np.ndarray) -> np.ndarray:
        phi = np.zeros(n_groups)
        for player in range(n_groups):
            for mask in range(n_masks):
                if mask >> player & 1:
                    continue
                size = bin(mask).count("1")
                weight = math.factorial(size) * math.factorial(n_groups - size - 1) / math.factorial(n_groups)
                phi[player] += weight * (values[mask | (1 << player)] - values[mask])
        return phi

    phi_views = shapley(value_views)
    phi_engagement = shapley(value_engagement)
    table = pd.DataFrame(
        {
            "group": GROUPS,
            "views_effect_log": phi_views,
            "views_multiplier": np.exp(phi_views),
            "engagement_effect_pp": phi_engagement * 100,
        }
    )
    return Explanation(
        table=table,
        baseline_views=max(0.0, float(np.expm1(value_views[0]))),
        forecast_views=max(0.0, float(np.expm1(value_views[-1]))),
        baseline_engagement=float(value_engagement[0]),
        forecast_engagement=float(value_engagement[-1]),
    )


# --------------------------------------------------------------------------- #
# 2. When should I publish?
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TimeGrid:
    table: pd.DataFrame  # long format: day, day_name, hour, views, engagement
    best_slots: pd.DataFrame
    chosen_views: float
    median_views: float

    @property
    def swing_pct(self) -> float:
        best = float(self.best_slots.iloc[0]["views"])
        return (best / max(self.median_views, 1.0) - 1.0) * 100.0


def time_grid(bundle: dict[str, object], draft: Draft, smooth: bool = True) -> TimeGrid:
    """Predict the same draft in all 168 weekly slots (IST).

    Forecasts are averaged with the neighbouring hours (circularly) so a single noisy
    leaf of a tree cannot create a fake "best minute"; this is a robustness choice,
    not a model change.
    """
    drafts = [draft.with_changes(day_of_week=day, publish_hour=hour) for day in range(7) for hour in range(24)]
    views_log, engagement = _predict_drafts(bundle, drafts)
    views_grid = views_log.reshape(7, 24)
    engagement_grid = engagement.reshape(7, 24)
    if smooth:
        views_grid = (np.roll(views_grid, 1, axis=1) + views_grid + np.roll(views_grid, -1, axis=1)) / 3
        engagement_grid = (np.roll(engagement_grid, 1, axis=1) + engagement_grid + np.roll(engagement_grid, -1, axis=1)) / 3

    table = pd.DataFrame(
        {
            "day": np.repeat(np.arange(7), 24),
            "day_name": np.repeat(DAYS, 24),
            "hour": np.tile(np.arange(24), 7),
            "views": np.expm1(views_grid).ravel(),
            "engagement": engagement_grid.ravel(),
        }
    )
    ranked = table.sort_values("views", ascending=False)
    chosen: list[pd.Series] = []
    for _, row in ranked.iterrows():
        near_existing = any(
            row["day"] == kept["day"] and min(abs(row["hour"] - kept["hour"]), 24 - abs(row["hour"] - kept["hour"])) <= 2
            for kept in chosen
        )
        if not near_existing:
            chosen.append(row)
        if len(chosen) == 3:
            break
    own = table[(table["day"] == draft.day_of_week) & (table["hour"] == draft.publish_hour)]
    return TimeGrid(
        table=table,
        best_slots=pd.DataFrame(chosen).reset_index(drop=True),
        chosen_views=float(own["views"].iloc[0]),
        median_views=float(table["views"].median()),
    )


# --------------------------------------------------------------------------- #
# 3. Which edits does the model associate with more views?
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Suggestion:
    key: str
    label: str
    why: str
    field: str  # which form field the edit changes: title / description / tags
    draft: Draft
    views: float
    views_change_pct: float
    engagement: float
    engagement_change_pp: float


def _keywords_for_tags(draft: Draft, limit: int = 5) -> list[str]:
    existing = {tag.casefold() for tag in normalise_tags(draft.tags).split("|")}
    return [word for word in title_words(draft.title) if word not in existing][:limit]


def _candidate_edits(draft: Draft) -> list[tuple[str, str, str, str, Draft]]:
    """(key, label, why, field, edited draft) - only edits that actually change something."""
    title = draft.title.strip()
    description = draft.description.strip()
    lowered = title.lower()
    tokens = set(_tokens(title))
    candidates: list[tuple[str, str, str, str, Draft]] = []

    def add(key: str, label: str, why: str, field: str, edited: Draft) -> None:
        if edited != draft:
            candidates.append((key, label, why, field, edited))

    # Only edits that keep the draft honest are offered. Edits that invent content (a made-up "Part 1", a fake "Latest:",
    # a placeholder link, or "How to" glued onto a sentence) were removed: a score cannot make a fabrication a good idea.
    if "?" not in title:
        add("question", "Phrase the title as a question", "Adds a question mark, which invites curiosity.",
            "title", draft.with_changes(title=title.rstrip(".!") + "?"))
    if "!" not in title:
        add("exclaim", "End the title with an exclamation mark", "Adds one exclamation mark (an energy signal).",
            "title", draft.with_changes(title=title.rstrip("?.") + "!"))
    if len(title) > 60:
        cut = title[:60].rsplit(" ", 1)[0].rstrip(",:;-")
        add("shorten", "Shorten the title to about 60 characters", "Shorter titles are fully visible in search results.",
            "title", draft.with_changes(title=cut))
    if title != title.title():
        add("title_case", "Use Title Case", "Raises the share of capital letters (caps ratio).",
            "title", draft.with_changes(title=title.title()))
    if title != title.capitalize() and title.upper() != title:
        add("sentence_case", "Use sentence case", "Lowers the share of capital letters (caps ratio).",
            "title", draft.with_changes(title=title.capitalize()))
    if not set(_tokens(description)) & CTA_WORDS:
        add("cta", "Add a call-to-action line to the description", "Adds subscribe/comment wording to the description.",
            "description", draft.with_changes(description=f"{description}\n\nSubscribe and tell us what you think in the comments.".strip()))
    if "#" not in description:
        words = title_words(title)[:3]
        if words:
            add("hashtags", "Add hashtags to the description", "Adds hashtags built from the main title words.",
                "description", draft.with_changes(description=f"{description}\n\n" + " ".join(f"#{word}" for word in words)))
    keywords = _keywords_for_tags(draft)
    if keywords:
        merged = normalise_tags(draft.tags)
        merged = ", ".join(keywords) if merged == "[none]" else merged.replace("|", ", ") + ", " + ", ".join(keywords)
        add("tag_keywords", "Reuse title keywords as tags", "Adds your own title keywords to the tag list.",
            "tags", draft.with_changes(tags=merged))
    return candidates


def suggest_edits(bundle: dict[str, object], draft: Draft) -> list[Suggestion]:
    """Score each candidate edit with the trained model and rank by predicted views."""
    candidates = _candidate_edits(draft)
    if not candidates:
        return []
    drafts = [draft] + [candidate[4] for candidate in candidates]
    views_log, engagement = _predict_drafts(bundle, drafts)
    base_views, base_engagement = float(np.expm1(views_log[0])), float(engagement[0])
    suggestions = []
    for (key, label, why, field, edited), vl, en in zip(candidates, views_log[1:], engagement[1:]):
        views = float(np.expm1(vl))
        suggestions.append(
            Suggestion(
                key=key, label=label, why=why, field=field, draft=edited,
                views=views,
                views_change_pct=(views / max(base_views, 1.0) - 1.0) * 100.0,
                engagement=float(en),
                engagement_change_pp=(float(en) - base_engagement) * 100.0,
            )
        )
    return sorted(suggestions, key=lambda item: item.views_change_pct, reverse=True)


# --------------------------------------------------------------------------- #
# 4. Category what-if
# --------------------------------------------------------------------------- #
def category_what_if(bundle: dict[str, object], draft: Draft) -> pd.DataFrame:
    """Same draft, every category with enough training videos."""
    reference = bundle["reference"]["categories"]
    names = sorted(reference)
    views_log, engagement = _predict_drafts(bundle, [draft.with_changes(category_name=name) for name in names])
    table = pd.DataFrame(
        {
            "category": names,
            "views": np.expm1(views_log),
            "engagement": engagement,
            "videos_in_data": [reference[name]["n"] for name in names],
            "is_selected": [name == draft.category_name for name in names],
        }
    )
    return table.sort_values("views", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 5. Keyword radar
# --------------------------------------------------------------------------- #
def keyword_signals(bundle: dict[str, object], title: str) -> pd.DataFrame:
    """Past performance of trending videos that share a word with this title."""
    stats = bundle["word_stats"]
    rows = [{"word": word, **stats[word]} for word in title_words(title) if word in stats]
    columns = ["word", "n", "n_channels", "median_views", "median_engagement", "views_lift", "engagement_lift"]
    return pd.DataFrame(rows, columns=columns).sort_values("views_lift", ascending=False).reset_index(drop=True)


def top_keywords(bundle: dict[str, object], n: int = 12, min_videos: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    stats = pd.DataFrame(bundle["word_stats"]).T.reset_index().rename(columns={"index": "word"})
    stats = stats[stats["n"] >= min_videos].sort_values("views_lift", ascending=False)
    return stats.head(n).reset_index(drop=True), stats.tail(n).iloc[::-1].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 6. Similar trending videos (nearest-neighbour second opinion)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SimilarResult:
    table: pd.DataFrame
    analog_median_views: float | None
    analog_median_engagement: float | None
    analogs_used: int


@lru_cache(maxsize=2)
def load_similarity_index(path: str = str(SIMILARITY_PATH)) -> dict[str, object]:
    if not Path(path).exists():
        raise FileNotFoundError(f"Similarity index not found at {path}. Run: python src/advanced_model.py --train")
    return joblib.load(path)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float | None:
    """Median that ignores values that are not numbers (a video with ratings switched off has no engagement rate)."""
    values, weights = np.asarray(values, dtype=float), np.asarray(weights, dtype=float)
    known = np.isfinite(values)
    if not known.any():
        return None
    values, weights = values[known], weights[known]
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cumulative = np.cumsum(weights)
    return float(values[np.searchsorted(cumulative, cumulative[-1] / 2.0)])


def similar_videos(index: dict[str, object], title: str, tags: str, k: int = 5, pool: int = 25,
                   min_similarity: float = 0.05) -> SimilarResult:
    query = index["vectorizer"].transform([similarity_text(title, normalise_tags(tags))])
    similarity = (index["matrix"] @ query.T).toarray().ravel()
    best = np.argsort(-similarity)[:pool]
    best = best[similarity[best] >= min_similarity]
    if len(best) == 0:
        empty = pd.DataFrame(columns=["title", "category", "views", "engagement", "similarity", "url"])
        return SimilarResult(empty, None, None, 0)
    table = pd.DataFrame(
        {
            "title": index["title"][best],
            "category": index["category"][best],
            "views": index["views"][best],
            "engagement": index["engagement"][best],
            "similarity": similarity[best],
            "url": [YOUTUBE_WATCH_URL + video_id for video_id in index["video_id"][best]],
        }
    )
    weights = similarity[best]
    return SimilarResult(
        table=table.head(k).reset_index(drop=True),
        analog_median_views=_weighted_median(index["views"][best], weights),
        analog_median_engagement=_weighted_median(index["engagement"][best], weights),
        analogs_used=int(len(best)),
    )


# --------------------------------------------------------------------------- #
# 7. Where does the forecast sit?
# --------------------------------------------------------------------------- #
def _percentile(sorted_values: np.ndarray, value: float) -> float:
    return float(np.searchsorted(sorted_values, value, side="right") / len(sorted_values) * 100.0)


def forecast_percentile(bundle: dict[str, object], category: str, views_log: float, engagement: float) -> dict[str, float | int | None]:
    """Compare a forecast with out-of-fold forecasts for real trending videos (like with like)."""
    reference = bundle["reference"]
    in_category = reference["categories"].get(category)
    return {
        "views_overall": _percentile(reference["views_oof_log_sorted"], views_log),
        "engagement_overall": _percentile(reference["engagement_oof_sorted"], engagement),
        "views_category": _percentile(in_category["views_oof_log_sorted"], views_log) if in_category else None,
        "engagement_category": _percentile(in_category["engagement_oof_sorted"], engagement) if in_category else None,
        "category_n": in_category["n"] if in_category else None,
    }


# --------------------------------------------------------------------------- #
# Strategy brief (downloadable summary)
# --------------------------------------------------------------------------- #
def _compact(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def build_brief_markdown(draft: Draft, prediction, explanation: Explanation, grid: TimeGrid,
                         suggestions: list[Suggestion]) -> str:
    low, high = prediction.views_ci_low, prediction.views_ci_high
    interval = f" (80% interval {_compact(low)} - {_compact(high)})" if low is not None else ""
    lines = [
        "# Pre-publication strategy brief",
        "",
        f"**Title:** {draft.title}",
        f"**Category:** {draft.category_name}  |  **Planned slot:** {DAYS[draft.day_of_week]} {draft.publish_hour:02d}:00 IST",
        "",
        "## Forecast",
        f"- Expected views: **{_compact(prediction.expected_views)}**{interval}",
        f"- Expected engagement rate: **{prediction.engagement_rate * 100:.2f}%**",
        "",
        "## Why (exact Shapley values over five feature groups)",
        f"- A typical trending video is forecast at {_compact(explanation.baseline_views)} views.",
    ]
    for _, row in explanation.table.sort_values("views_effect_log", key=abs, ascending=False).iterrows():
        lines.append(f"- {row['group']}: x{row['views_multiplier']:.2f} on views")
    lines += ["", "## Best publishing slots (IST)"]
    for _, row in grid.best_slots.iterrows():
        lines.append(f"- {row['day_name']} {int(row['hour']):02d}:00 -> about {_compact(row['views'])} views")
    if suggestions:
        lines += ["", "## Edits the model associates with higher views"]
        for item in suggestions[:5]:
            lines.append(f"- {item.label}: {item.views_change_pct:+.1f}% views, {item.engagement_change_pp:+.2f} pp engagement")
    lines += [
        "",
        "_Associations in India-trending videos (2017-2018), not causal promises. "
        "Thumbnails, channel size and YouTube's ranking are not modelled._",
    ]
    return "\n".join(lines) + "\n"


__all__ = [
    "DAYS", "GROUPS", "Draft", "Explanation", "Suggestion", "SimilarResult", "TimeGrid",
    "STOPWORDS", "build_brief_markdown", "category_what_if", "explain_groups",
    "forecast_percentile", "input_group", "keyword_signals", "load_similarity_index",
    "similar_videos", "suggest_edits", "time_grid", "top_keywords",
]
