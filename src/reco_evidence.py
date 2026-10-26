"""Evidence packet: the only facts the recommendation layer (LLM or rules) may rely on.

Every fact is computed by the existing ML/insight functions; nothing here predicts anything.
The ``Prediction`` object is carried through unchanged so a recommendation can never
overwrite a forecast.  Each fact has an id (E1, E2, ...) that recommendations must cite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.inference import Prediction, global_feature_groups, predict_video
from src.insights import (
    Draft,
    _compact,
    explain_groups,
    forecast_percentile,
    keyword_signals,
    similar_videos,
    suggest_edits,
    time_grid,
)

DATASET_LIMIT = (
    "The data holds only India-trending videos (2017-2018): it estimates relative performance among videos that "
    "already trended, not whether an arbitrary upload will go viral, and it cannot see thumbnails, channel size, "
    "retention or YouTube's ranking."
)
TIMING_GAP_THRESHOLD_PCT = 5.0  # the planned slot must trail the best slot by this much before timing advice is allowed
MIN_EDIT_EFFECT_PCT = 2.0       # smaller model-scored changes are treated as noise


def ordinal(value: float) -> str:
    number = int(round(value))
    suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


@dataclass(frozen=True)
class Fact:
    id: str
    kind: str
    text: str
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EvidencePacket:
    draft: Draft
    prediction: Prediction
    facts: tuple[Fact, ...]
    gates: dict[str, bool]

    def by_kind(self, kind: str) -> list[Fact]:
        return [fact for fact in self.facts if fact.kind == kind]

    @property
    def ids(self) -> set[str]:
        return {fact.id for fact in self.facts}

    def corpus(self) -> str:
        """All fact text; used to check that numbers quoted by a recommendation exist in the evidence."""
        return " ".join(fact.text for fact in self.facts)

    def to_prompt_payload(self) -> dict:
        draft = self.draft
        return {
            "draft": {
                "title": draft.title, "tags": draft.tags, "description": draft.description[:1500],
                "category": draft.category_name, "publish_day": draft.day_of_week, "publish_hour_ist": draft.publish_hour,
            },
            "facts": [{"id": fact.id, "kind": fact.kind, "text": fact.text} for fact in self.facts],
            "advice_allowed": dict(self.gates),
        }


def build_evidence(bundle: dict[str, object], draft: Draft, similarity_index: dict | None = None) -> EvidencePacket:
    prediction = predict_video(
        bundle, title=draft.title, tags=draft.tags, description=draft.description,
        category_name=draft.category_name, day_of_week=draft.day_of_week, publish_hour=draft.publish_hour,
    )
    facts: list[Fact] = []

    def add(kind: str, text: str, **data: object) -> None:
        facts.append(Fact(f"E{len(facts) + 1}", kind, text, data))

    # 1. The forecast itself (ML numbers, copied from the Prediction object)
    pct = forecast_percentile(bundle, draft.category_name, prediction.views_log, prediction.engagement_rate)
    add("forecast",
        f"Model forecast: {_compact(prediction.expected_views)} views (80% interval {_compact(prediction.views_ci_low)} to "
        f"{_compact(prediction.views_ci_high)}) and {prediction.engagement_rate * 100:.2f}% engagement (80% interval "
        f"{prediction.engagement_ci_low * 100:.2f}% to {prediction.engagement_ci_high * 100:.2f}%). The views forecast is at the "
        f"{ordinal(pct['views_overall'])} percentile of trending videos"
        + (f" ({ordinal(pct['views_category'])} within {draft.category_name}, n={pct['category_n']})." if pct["views_category"] is not None else "."),
        expected_views=prediction.expected_views, engagement_rate=prediction.engagement_rate, percentiles=pct)
    calibration = bundle["calibration"]
    cover = calibration["coverage_check"]
    add("uncertainty",
        f"Intervals are calibrated: they held {cover['views_chronological_holdout'] * 100:.0f}% (views) and "
        f"{cover['engagement_chronological_holdout'] * 100:.0f}% (engagement) of the time on later uploads. A views forecast is "
        f"typically within x{calibration['views_multiplier_low']:.2f} to x{calibration['views_multiplier_high']:.2f} of the truth, "
        "so small differences are within model uncertainty.")
    if prediction.out_of_range_features:
        names = ", ".join(name.replace("_", " ") for name in prediction.out_of_range_features[:4])
        add("out_of_range", f"The draft is outside the central 90% of the training data for: {names}; the forecast is less stable.",
            features=list(prediction.out_of_range_features))

    # 2. Which groups of choices drive this forecast (exact Shapley values)
    explanation = explain_groups(bundle, draft)
    table = explanation.table.sort_values("views_effect_log")
    for row in table.itertuples():
        change = (row.views_multiplier - 1) * 100
        add("shapley", f"{row.group} moves the views forecast by {change:+.0f}% vs a typical trending video "
            f"({row.engagement_effect_pp:+.2f} pp engagement).", group=row.group, change_pct=float(change))
    groups = global_feature_groups(bundle)
    top_group = groups[groups["target"] == "views_log"].iloc[0]
    add("importance", f"Across the whole dataset the views model relies most on: {top_group['group']} "
        f"({top_group['importance'] * 100:.0f}% of importance).", group=str(top_group["group"]))

    # 3. Category benchmark (dataset statistics)
    reference = bundle["reference"]["categories"].get(draft.category_name)
    gates = {"timing": False, "category": reference is not None}
    if reference:
        add("category", f"In {draft.category_name} (n={reference['n']} trending videos) the median is "
            f"{_compact(reference['median_views'])} views and {reference['median_engagement'] * 100:.2f}% engagement.",
            n=reference["n"], median_views=reference["median_views"])

    # 4. Model-scored edits (each one re-scored by the trained model)
    suggestions = suggest_edits(bundle, draft)
    for item in [s for s in suggestions if s.views_change_pct >= MIN_EDIT_EFFECT_PCT][:4]:
        add("edit_up", f"Model-scored edit '{item.label}' changes the views forecast by {item.views_change_pct:+.1f}% "
            f"and engagement by {item.engagement_change_pp:+.2f} pp.", key=item.key, field=item.field,
            views_change_pct=item.views_change_pct, label=item.label, why=item.why, draft=item.draft)
    for item in [s for s in suggestions if s.views_change_pct <= -MIN_EDIT_EFFECT_PCT][-2:]:
        add("edit_down", f"Model-scored edit '{item.label}' would lower the views forecast by {abs(item.views_change_pct):.1f}%.",
            key=item.key, field=item.field, views_change_pct=item.views_change_pct, label=item.label)

    # 5. Title keywords that exist in the dataset statistics
    for row in keyword_signals(bundle, draft.title).head(3).itertuples():
        add("keyword", f"Trending videos with '{row.word}' in the title (n={int(row.n)}, {int(row.n_channels)} channels) have median "
            f"{_compact(row.median_views)} views (x{row.views_lift:.2f} of typical).", word=row.word)

    # 6. Timing (advice only if the planned slot clearly trails the best one)
    grid = time_grid(bundle, draft)
    best = grid.best_slots.iloc[0]
    gap_pct = (grid.chosen_views / max(float(best["views"]), 1.0) - 1) * 100
    gates["timing"] = gap_pct <= -TIMING_GAP_THRESHOLD_PCT
    add("timing", f"Best slot for this draft is {best['day_name']} {int(best['hour']):02d}:00 IST ({_compact(best['views'])} views); "
        f"the planned slot is {gap_pct:+.0f}% vs that. The best slot is {grid.swing_pct:+.0f}% above the median slot, so timing is a small effect.",
        gap_pct=float(gap_pct), best_day=str(best["day_name"]), best_hour=int(best["hour"]))

    # 7. Look-alike second opinion (optional)
    if similarity_index is not None:
        similar = similar_videos(similarity_index, draft.title, draft.tags)
        if similar.analog_median_views:
            add("analogs", f"{similar.analogs_used} look-alike trending videos have median {_compact(similar.analog_median_views)} views "
                f"(model forecast {_compact(prediction.expected_views)}).", analog_median=similar.analog_median_views)

    add("limits", DATASET_LIMIT)
    return EvidencePacket(draft=draft, prediction=prediction, facts=tuple(facts), gates=gates)

