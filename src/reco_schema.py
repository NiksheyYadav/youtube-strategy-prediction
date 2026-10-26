"""Schema and validators for recommendations (LLM output or rule-based).

Nothing from a language model is displayed until it passes ``parse_and_validate``.  The schema has no
numeric forecast fields, every claim must cite evidence ids from the packet, numbers quoted with a
unit (%, K, M, pp, x) must exist in the evidence, and over-confident wording is rejected.
"""

from __future__ import annotations

import json
import re

import jsonschema

from src.insights_artifacts import title_words
from src.reco_evidence import EvidencePacket

_EVIDENCE = {"type": "array", "minItems": 1, "maxItems": 4, "items": {"type": "string", "pattern": r"^E\d{1,2}$"}}
_TEXT = lambda limit, low=1: {"type": "string", "minLength": low, "maxLength": limit}  # noqa: E731

RECOMMENDATION_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "priorities", "weaknesses", "title_alternatives", "tag_suggestions",
                 "description_advice", "timing_category_advice", "limitations"],
    "properties": {
        "summary": _TEXT(600),
        "priorities": {"type": "array", "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["action", "why", "evidence", "confidence"],
            "properties": {"action": _TEXT(220), "why": _TEXT(320), "evidence": _EVIDENCE,
                           "confidence": {"enum": ["low", "moderate"]}}}},
        "weaknesses": {"type": "array", "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["field", "issue", "why", "evidence"],
            "properties": {"field": {"enum": ["title", "description", "tags", "timing", "category"]},
                           "issue": _TEXT(220), "why": _TEXT(320), "evidence": _EVIDENCE}}},
        "title_alternatives": {"type": "array", "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["title", "rationale", "evidence"],
            "properties": {"title": _TEXT(100, 4), "rationale": _TEXT(260), "evidence": _EVIDENCE}}},
        "tag_suggestions": {"type": "object", "additionalProperties": False, "required": ["add", "rationale"],
                            "properties": {"add": {"type": "array", "maxItems": 8, "items": _TEXT(30, 2)},
                                           "rationale": _TEXT(260, 0),
                                           "evidence": {"type": "array", "maxItems": 4, "items": {"type": "string", "pattern": r"^E\d{1,2}$"}}}},
        "description_advice": {"type": "array", "maxItems": 2, "items": {
            "type": "object", "additionalProperties": False, "required": ["change", "why", "evidence"],
            "properties": {"change": _TEXT(260), "why": _TEXT(320), "evidence": _EVIDENCE}}},
        "timing_category_advice": {"type": "object", "additionalProperties": False, "required": ["advice", "evidence"],
                                   "properties": {"advice": {"type": ["string", "null"], "maxLength": 320},
                                                  "evidence": {"type": "array", "maxItems": 4, "items": {"type": "string", "pattern": r"^E\d{1,2}$"}}}},
        "limitations": {"type": "array", "minItems": 1, "maxItems": 3, "items": _TEXT(300)},
    },
}

OVERCONFIDENT = re.compile(
    r"\b(definitely|certainly|surely|guaranteed|sure to|100\s?%|will (?:definitely |certainly )?"
    r"(?:go viral|increase|boost|double|triple|skyrocket|explode|get you|bring))\b", re.IGNORECASE)
_NEGATION = ("whether", " if ", "cannot", "can't", "can not", "not ", "n't", " no ", "never", "unlikely to")


def overconfident(text: str) -> bool:
    """True for assertive promises; negated or conditional phrasing ('cannot say whether it will go viral') is fine."""
    for match in OVERCONFIDENT.finditer(text):
        before = text[max(0, match.start() - 45):match.start()].lower()
        if not any(token in f" {before}" for token in _NEGATION):
            return True
    return False


MARKUP = re.compile(r"https?://|www\.|<[^>]+>|\]\(")
_NUMBER = re.compile(r"(?<![\w.])[+\-]?(\d+(?:[.,]\d+)?)\s*(%|pp\b|[KkMm]\b)|\bx(\d+(?:\.\d+)?)", re.IGNORECASE)


class InvalidRecommendation(ValueError):
    """Raised when a recommendation fails schema or evidence checks; ``errors`` lists every problem."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors[:5]))
        self.errors = errors


def quoted_numbers(text: str) -> list[tuple[float, str]]:
    found = []
    for match in _NUMBER.finditer(text):
        if match.group(3):
            found.append((float(match.group(3)), "x"))
        else:
            unit = match.group(2).lower()
            found.append((float(match.group(1).replace(",", ".")), unit))
    return found


def _walk_strings(value, path=""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")


def _evidence_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence":
                yield from item
            else:
                yield from _evidence_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _evidence_refs(item)


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0.0


def validate_recommendation(data: object, packet: EvidencePacket) -> list[str]:
    """Return a list of problems (empty = valid)."""
    validator = jsonschema.Draft202012Validator(RECOMMENDATION_SCHEMA)
    errors = [f"schema: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:120]}" for e in validator.iter_errors(data)]
    if errors:
        return errors[:8]
    assert isinstance(data, dict)

    unknown = sorted(set(_evidence_refs(data)) - packet.ids)
    if unknown:
        errors.append(f"evidence: unknown ids {unknown}")

    allowed = quoted_numbers(packet.corpus())
    for path, text in _walk_strings({k: v for k, v in data.items() if k != "title_alternatives"}):
        if overconfident(text):
            errors.append(f"claims: over-confident wording in {path}")
        if MARKUP.search(text):
            errors.append(f"markup: links or HTML in {path}")
        for value, unit in quoted_numbers(text):
            if not any(unit == u and abs(value - v) <= max(0.06, 0.02 * v) for v, u in allowed):
                errors.append(f"numbers: {value:g}{unit} in {path} is not in the evidence")

    draft = packet.draft
    advice = data["timing_category_advice"]
    if advice["advice"] and not (packet.gates["timing"] or packet.gates["category"]):
        errors.append("gate: timing/category advice given although the evidence does not support it")
    if advice["advice"] and not advice["evidence"]:
        errors.append("evidence: timing/category advice cites no evidence")

    original_words = set(title_words(draft.title))
    context_words = original_words | set(title_words(draft.description)) | set(title_words(draft.tags.replace("|", " ")))
    for index, item in enumerate(data["title_alternatives"]):
        title = item["title"]
        path = f"title_alternatives[{index}]"
        if title.strip().lower() == draft.title.strip().lower():
            errors.append(f"title: {path} repeats the current title")
        if _caps_ratio(title) > 0.6 and len(title) > 8:
            errors.append(f"title: {path} is mostly capitals")
        if MARKUP.search(title) or title.count("!") > 1 or overconfident(title):
            errors.append(f"title: {path} has markup, repeated exclamation marks or over-confident wording")
        words = set(title_words(title))
        if len(original_words) >= 2 and len(words & context_words) < max(1, round(0.4 * len(original_words))):
            errors.append(f"title: {path} drifts away from the draft's own words")
    existing = {t.strip().lower() for t in draft.tags.replace("|", ",").split(",") if t.strip()}
    added = [t.strip().lower().lstrip("#") for t in data["tag_suggestions"]["add"]]
    if len(set(added)) != len(added) or existing & set(added):
        errors.append("tags: suggestions repeat each other or existing tags")
    return errors


def _loads(text: str) -> object:
    stripped = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        raise InvalidRecommendation(["json: no JSON object found"])
    try:
        return json.loads(stripped[start:end + 1])
    except json.JSONDecodeError as error:
        raise InvalidRecommendation([f"json: {error.msg} at position {error.pos}"]) from error


def parse_and_validate(text: str, packet: EvidencePacket) -> dict:
    data = _loads(text)
    errors = validate_recommendation(data, packet)
    if errors:
        raise InvalidRecommendation(errors)
    return data  # type: ignore[return-value]
