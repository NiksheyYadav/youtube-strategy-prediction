"""Validator and rule-based recommender: good output passes, every kind of bad output is rejected."""

from __future__ import annotations

import copy
import json

import pytest

from src.golden import GOLDEN_DRAFTS
from src.inference import load_bundle
from src.reco_evidence import EvidencePacket, build_evidence
from src.reco_schema import InvalidRecommendation, parse_and_validate, quoted_numbers, validate_recommendation
from src.recommendations import rules_recommendation


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.fixture(scope="module")
def packet(bundle):
    return build_evidence(bundle, GOLDEN_DRAFTS["education"])


@pytest.fixture(scope="module")
def good(packet):
    return rules_recommendation(packet)


@pytest.mark.parametrize("name", sorted(GOLDEN_DRAFTS))
def test_rule_based_output_is_valid_for_every_golden_draft(bundle, name):
    packet = build_evidence(bundle, GOLDEN_DRAFTS[name])
    assert validate_recommendation(rules_recommendation(packet), packet) == []


def test_valid_json_round_trips_inside_code_fences_and_chatter(packet, good):
    assert parse_and_validate("```json\n" + json.dumps(good) + "\n```", packet)["summary"] == good["summary"]
    assert parse_and_validate("Here you go: " + json.dumps(good) + " Hope it helps!", packet)


def _mutated(good, mutate):
    data = copy.deepcopy(good)
    mutate(data)
    return data


EDU_TITLE = GOLDEN_DRAFTS["education"].title

BAD_CASES = [
    ("unknown evidence id", lambda d: d["priorities"][0].update(evidence=["E99"]), "unknown ids"),
    ("missing evidence", lambda d: d["priorities"][0].update(evidence=[]), "schema"),
    ("extra field", lambda d: d.update(predicted_views=123456), "schema"),
    ("numeric forecast override", lambda d: d.update(expected_views=999), "schema"),
    ("too many priorities", lambda d: d.update(priorities=d["priorities"][:1] * 4), "schema"),  # four copies: always over the limit of three
    ("bad confidence value", lambda d: d["priorities"][0].update(confidence="high"), "schema"),
    ("promise", lambda d: d.update(summary="This will definitely go viral."), "over-confident"),
    ("will boost", lambda d: d["priorities"][0].update(why="This edit will double your views."), "over-confident"),
    ("invented number", lambda d: d.update(summary="Expect 9.9M views and 77% engagement."), "not in the evidence"),
    ("link in text", lambda d: d["priorities"][0].update(why="See https://evil.example now"), "links or HTML"),
    ("html in text", lambda d: d["priorities"][0].update(action="<b>Do this</b>"), "links or HTML"),
    ("title repeats", lambda d: d.update(title_alternatives=[{"title": EDU_TITLE.lower(), "rationale": "same", "evidence": ["E1"]}]), "repeats"),
    ("title shouting", lambda d: d.update(title_alternatives=[{"title": "5 STUDY TIPS THAT ACTUALLY WORK", "rationale": "loud", "evidence": ["E1"]}]), "capitals"),
    ("title drifts", lambda d: d.update(title_alternatives=[{"title": "Celebrity gossip you will not believe", "rationale": "x", "evidence": ["E1"]}]), "drifts"),
    ("duplicate tags", lambda d: d["tag_suggestions"].update(add=["Study Tips"]), "repeat"),
    ("empty limitations", lambda d: d.update(limitations=[]), "schema"),
]


@pytest.mark.parametrize("label, mutate, expected", BAD_CASES, ids=[c[0] for c in BAD_CASES])
def test_bad_output_is_rejected(packet, good, label, mutate, expected):
    errors = validate_recommendation(_mutated(good, mutate), packet)
    assert errors and any(expected in e for e in errors), (label, errors)


def test_timing_advice_is_rejected_when_the_evidence_does_not_support_it(bundle):
    packet = build_evidence(bundle, GOLDEN_DRAFTS["music"])
    ungated = EvidencePacket(packet.draft, packet.prediction, packet.facts, {"timing": False, "category": False})
    data = rules_recommendation(packet)
    data["timing_category_advice"] = {"advice": "Move to Friday evening.", "evidence": ["E1"]}
    assert any("gate" in e for e in validate_recommendation(data, ungated))


@pytest.mark.parametrize("text", ["", "not json", "{broken", "[1, 2]", "null"])
def test_malformed_text_raises(packet, text):
    with pytest.raises(InvalidRecommendation):
        parse_and_validate(text, packet)


def test_negated_claims_and_disclaimers_are_allowed(packet, good):
    data = copy.deepcopy(good)
    data["limitations"] = ["We cannot say whether an upload will go viral; this is not a guarantee."]
    assert validate_recommendation(data, packet) == []


def test_number_extraction_understands_units():
    assert quoted_numbers("+16.0% and 85.6K, 1.2M plus x0.29 and 0.5 pp") == [
        (16.0, "%"), (85.6, "k"), (1.2, "m"), (0.29, "x"), (0.5, "pp")]
