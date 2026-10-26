"""Recommendation engine: rule-based baseline now, optional on-device LLM layered on top.

The ML forecast is never produced or altered here.  ``rules_recommendation`` builds a schema-valid
recommendation straight from the evidence packet, so the feature works with no language model at all.
"""

from __future__ import annotations

from src.advanced_model import normalise_tags
from src.reco_evidence import DATASET_LIMIT, EvidencePacket
from src.reco_schema import _caps_ratio

EDITABLE_GROUPS = {"Title packaging": "title", "Tags": "tags", "Description": "description"}
FIELD_BY_PREFIX = (("tag_", "tags"), ("description_", "description"), ("publish_", "timing"), ("is_weekend", "timing"))
WEAK_GROUP_PCT = -3.0


def _field_for_feature(name: str) -> str:
    for prefix, field in FIELD_BY_PREFIX:
        if name.startswith(prefix):
            return field
    return "title"


def _tags(raw: str) -> list[str]:
    return [t for t in normalise_tags(raw).split("|") if t and t != "[none]"]


def rules_recommendation(packet: EvidencePacket) -> dict:
    """A schema-valid recommendation computed only from model-scored evidence (no language model)."""
    forecast = packet.by_kind("forecast")[0]
    ups = packet.by_kind("edit_up")
    timing = packet.by_kind("timing")[0]
    priorities: list[dict] = []
    for fact in ups[:2]:
        priorities.append({"action": fact.data["label"], "why": fact.text, "evidence": [fact.id], "confidence": "low"})
    if packet.gates["timing"] and len(priorities) < 3:
        priorities.append({"action": f"Consider publishing {timing.data['best_day']} {timing.data['best_hour']:02d}:00 IST",
                           "why": timing.text, "evidence": [timing.id], "confidence": "low"})
    if not priorities:
        priorities.append({"action": "Keep the draft as it is: no tested edit changed the forecast enough to rise above model noise",
                           "why": forecast.text, "evidence": [forecast.id], "confidence": "low"})

    weaknesses: list[dict] = []
    for fact in packet.by_kind("shapley"):
        if fact.data["group"] in EDITABLE_GROUPS and fact.data["change_pct"] <= WEAK_GROUP_PCT and len(weaknesses) < 2:
            weaknesses.append({"field": EDITABLE_GROUPS[fact.data["group"]],
                               "issue": f"{fact.data['group']} lowers the forecast versus a typical trending video",
                               "why": fact.text, "evidence": [fact.id]})
    for fact in packet.by_kind("out_of_range")[:1]:
        weaknesses.append({"field": _field_for_feature(fact.data["features"][0]),
                           "issue": "Unusual compared with the training data", "why": fact.text, "evidence": [fact.id]})

    title_alternatives = [
        {"title": fact.data["draft"].title, "rationale": f"{fact.data['why']} (model-scored edit)", "evidence": [fact.id]}
        for fact in ups if fact.data["field"] == "title" and len(fact.data["draft"].title) <= 100  # YouTube title limit
        and _caps_ratio(fact.data["draft"].title) <= 0.6  # never endorse shouting
    ][:3]
    description_advice = [
        {"change": fact.data["label"], "why": fact.text, "evidence": [fact.id]}
        for fact in ups if fact.data["field"] == "description"
    ][:2]

    tag_fact = next((f for f in ups if f.data["field"] == "tags"), None)
    if tag_fact:
        original = {t.lower() for t in _tags(packet.draft.tags)}
        new = [t for t in _tags(tag_fact.data["draft"].tags) if t.lower() not in original][:8]
        tag_suggestions = {"add": new, "rationale": "Reuses your own title keywords as tags (model-scored edit).", "evidence": [tag_fact.id]}
    else:
        tag_suggestions = {"add": [], "rationale": "No tag change was large enough to rise above model noise.", "evidence": []}

    advice = {"advice": timing.text, "evidence": [timing.id]} if packet.gates["timing"] else {"advice": None, "evidence": []}
    uncertainty = packet.by_kind("uncertainty")[0]
    return {
        "summary": forecast.text,
        "priorities": priorities[:3],
        "weaknesses": weaknesses[:3],
        "title_alternatives": title_alternatives,
        "tag_suggestions": tag_suggestions,
        "description_advice": description_advice,
        "timing_category_advice": advice,
        "limitations": [DATASET_LIMIT, uncertainty.text],
    }
