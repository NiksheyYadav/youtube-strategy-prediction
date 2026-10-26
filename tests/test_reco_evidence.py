"""Evidence packets carry the ML numbers unchanged and gate advice on the data."""

from __future__ import annotations

import json

import pytest

from src.golden import GOLDEN_DRAFTS
from src.inference import load_bundle, predict_video
from src.insights import Draft, load_similarity_index
from src.reco_evidence import DATASET_LIMIT, build_evidence


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.mark.parametrize("name", sorted(GOLDEN_DRAFTS))
def test_packet_prediction_equals_a_direct_model_call(bundle, name):
    draft = GOLDEN_DRAFTS[name]
    packet = build_evidence(bundle, draft)
    direct = predict_video(bundle, title=draft.title, tags=draft.tags, description=draft.description,
                           category_name=draft.category_name, day_of_week=draft.day_of_week, publish_hour=draft.publish_hour)
    # multi-threaded tree aggregation can differ in the last floating-point digit
    assert packet.prediction.expected_views == pytest.approx(direct.expected_views, rel=1e-9)
    assert packet.prediction.engagement_rate == pytest.approx(direct.engagement_rate, rel=1e-9)
    assert packet.by_kind("forecast")[0].data["expected_views"] == pytest.approx(direct.expected_views, rel=1e-9)


def test_ids_are_unique_sequential_and_payload_is_compact_json(bundle):
    packet = build_evidence(bundle, GOLDEN_DRAFTS["education"], load_similarity_index())
    ids = [fact.id for fact in packet.facts]
    assert ids == [f"E{i}" for i in range(1, len(ids) + 1)]
    payload = json.dumps(packet.to_prompt_payload())
    assert len(payload) < 9000  # keeps a local model's prompt small
    assert any(fact.kind == "limits" and fact.text == DATASET_LIMIT for fact in packet.facts)


def test_every_fact_kind_expected_for_a_normal_draft_is_present(bundle):
    kinds = {fact.kind for fact in build_evidence(bundle, GOLDEN_DRAFTS["education"], load_similarity_index()).facts}
    assert {"forecast", "uncertainty", "shapley", "importance", "category", "timing", "limits", "analogs"} <= kinds


def test_timing_advice_is_gated_on_the_gap_to_the_best_slot(bundle):
    packet = build_evidence(bundle, GOLDEN_DRAFTS["education"])
    gap = packet.by_kind("timing")[0].data["gap_pct"]
    assert packet.gates["timing"] == (gap <= -5.0)


def test_unknown_category_has_no_category_benchmark_and_no_category_advice(bundle):
    draft = Draft("A title", "a, b", "desc", "No Such Category", 1, 9)
    packet = build_evidence(bundle, draft)
    assert packet.gates["category"] is False and not packet.by_kind("category")


def test_building_evidence_is_deterministic(bundle):
    a = build_evidence(bundle, GOLDEN_DRAFTS["music"])
    b = build_evidence(bundle, GOLDEN_DRAFTS["music"])
    assert [f.text for f in a.facts] == [f.text for f in b.facts] and a.gates == b.gates
