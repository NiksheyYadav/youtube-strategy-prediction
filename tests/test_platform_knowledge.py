import copy
import json
from urllib.parse import urlparse

import pytest

from src.inference import load_bundle
from src.insights import Draft
from src.platform_knowledge import (
    KNOWLEDGE_PATH,
    SOURCE_TYPES,
    date_label,
    fact_text,
    load_timeline,
    select_entries,
    validate_entries,
    view_count_note,
)
from src.reco_evidence import build_evidence
from src.reco_schema import validate_recommendation
from src.recommendations import SYSTEM_PROMPT, rules_recommendation

OFFICIAL_HOSTS = {"blog.youtube", "support.google.com", "youtube.googleblog.com"}
RESEARCH_HOSTS = {"consensus.app", "dl.acm.org", "doi.org", "arxiv.org"}
DRAFT = Draft("Study tips for students", "study|tips", "Simple tips for exams.", "Education", 1, 18)


@pytest.fixture(scope="module")
def raw():
    return json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entries():
    return load_timeline()


def test_the_shipped_file_is_valid_and_says_it_is_not_the_algorithm(raw):
    assert validate_entries(raw) == []
    assert len(raw["entries"]) >= 15
    assert "does not publish its ranking formula" in raw["about"] and "nothing here is 'the algorithm'" in raw["about"]


def test_every_entry_is_sourced_to_a_trustworthy_kind_of_place(entries):
    for entry in entries:
        host = urlparse(entry.source["url"]).hostname
        if entry.source_type == "official":
            assert host in OFFICIAL_HOSTS, f"{entry.id}: an 'official' entry must link to YouTube/Google, not {host}"
        elif entry.source_type == "peer_reviewed":
            assert host in RESEARCH_HOSTS, f"{entry.id}: a research entry must link to a paper or a paper index, not {host}"
        else:
            assert entry.source_type == "press_report" and "press" in entry.source["publisher"].lower()
        assert entry.verified["on"] >= "2026-01-01" and entry.verified["how"]


def test_entries_are_in_date_order_and_cover_the_recent_years(entries):
    keys = [entry.sort_key for entry in entries]
    assert keys == sorted(keys)
    covered_years = {entry.period[:4] for entry in entries if entry.period != "undated"}
    assert {"2019", "2021", "2025", "2026"} <= covered_years


def test_dates_are_never_shown_more_precisely_than_the_source_gives(entries):
    by_id = {entry.id: entry for entry in entries}
    assert date_label(by_id["K10"]) == "24 Aug 2026"
    assert date_label(by_id["K09"]) == "Jul 2025"           # press: month only
    assert date_label(by_id["K06"]) == "2023"               # the blog gives no exact start date
    assert date_label(by_id["K11"]) == "undated"


def test_press_entries_are_labelled_as_lower_confidence_in_the_evidence_text(entries):
    press = [entry for entry in entries if entry.source_type == "press_report"]
    assert press, "the Trending-page entry is press-only and must stay labelled"
    for entry in press:
        assert "press report (lower confidence)" in fact_text(entry)


@pytest.mark.parametrize("mutation, expected", [
    (lambda e: e["entries"][0]["source"].update(type="blog_post"), "source type"),
    (lambda e: e["entries"][0]["source"].update(url="http://insecure.example/"), "https link"),
    (lambda e: e["entries"][0].pop("what_changed"), "missing 'what_changed'"),
    (lambda e: e["entries"][0].update(verified={}), "'verified' needs"),
    (lambda e: e["entries"][1].update(id=e["entries"][0]["id"]), "duplicate id"),
    (lambda e: e["entries"][1].update(date_precision="day", period="2019"), "'day' period"),
    (lambda e: [x for x in e["entries"] if x["source"]["type"] == "press_report"][0]["source"].update(publisher="Some Outlet"), "press"),
    (lambda e: e.update(entries=[]), "non-empty"),
])
def test_the_validator_rejects_unsourced_or_mislabelled_entries(raw, mutation, expected):
    broken = copy.deepcopy(raw)
    mutation(broken)
    assert any(expected in problem for problem in validate_entries(broken)), validate_entries(broken)


def test_only_a_few_relevant_entries_reach_the_prompt(entries):
    assert [e.id for e in select_entries({"timing": False}, entries)] == ["K11", "K12"]
    assert [e.id for e in select_entries({"timing": True}, entries)] == ["K11", "K12", "K13"]


def test_evidence_carries_platform_facts_with_their_sources_and_the_counting_caveat():
    bundle = load_bundle()
    packet = build_evidence(bundle, DRAFT)
    platform = packet.by_kind("platform")
    assert {fact.data["kb_id"] for fact in platform} >= {"K11", "K12"}
    assert all("Source:" in fact.text and fact.data["url"].startswith("https://") for fact in platform)
    note = packet.by_kind("platform_note")[0].text
    assert note == view_count_note("India 2017-2018") and "24 Aug 2026" in note and "2017-2018" in note
    assert packet.gates["platform"] is True
    assert [fact.id for fact in packet.facts] == [f"E{i}" for i in range(1, len(packet.facts) + 1)]
    assert packet.facts[-1].kind == "limits"


def test_the_counting_caveat_appears_in_the_rule_based_limitations_and_still_validates():
    packet = build_evidence(load_bundle(), DRAFT)
    recommendation = rules_recommendation(packet)
    assert any("24 Aug 2026" in text for text in recommendation["limitations"]) and len(recommendation["limitations"]) <= 3
    assert validate_recommendation(recommendation, packet) == []


def test_the_prompt_tells_the_model_how_to_use_platform_facts():
    assert "kind platform" in SYSTEM_PROMPT and "secret formula" in SYSTEM_PROMPT


def test_a_missing_or_broken_knowledge_file_does_not_break_the_coach(monkeypatch):
    import src.reco_evidence as evidence

    def broken(gates):
        raise OSError("knowledge file missing")

    monkeypatch.setattr(evidence, "select_entries", broken)
    packet = build_evidence(load_bundle(), DRAFT)
    assert packet.gates["platform"] is False and not packet.by_kind("platform")
    assert validate_recommendation(rules_recommendation(packet), packet) == []
