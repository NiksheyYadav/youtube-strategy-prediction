"""Sourced knowledge about how YouTube recommends and counts videos (knowledge/youtube_platform_timeline.json).

What this is: documented changes and statements that YouTube or researchers have published, each with its source, the
type of source and how it was verified.  What it is not: YouTube's ranking formula, which is not public.  Entries from
press coverage are labelled as such.  The AI Coach may mention only the entries that reach it as evidence facts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = ROOT / "knowledge" / "youtube_platform_timeline.json"
SOURCE_TYPES = {"official": "official YouTube page", "peer_reviewed": "peer-reviewed paper", "press_report": "press report (lower confidence)"}
PRECISIONS = {"day", "month", "year", "undated"}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ALWAYS_SHOWN = ("K11", "K12")  # what YouTube says drives recommendations; titles and thumbnails
TIMING_ENTRY = "K13"           # shown only when timing advice is on the table
REQUIRED = ("id", "period", "date_precision", "topic", "title", "what_changed", "creator_takeaway", "source", "verified")
SOURCE_REQUIRED = ("url", "title", "publisher", "type", "published")


@dataclass(frozen=True)
class Entry:
    id: str
    period: str
    date_precision: str
    topic: str
    title: str
    what_changed: str
    creator_takeaway: str
    source: dict
    verified: dict

    @property
    def source_type(self) -> str:
        return str(self.source["type"])

    @property
    def sort_key(self) -> str:
        return self.period if self.period != "undated" else "9999"


def validate_entries(raw: object) -> list[str]:
    """Every problem with the knowledge file (empty list = valid): each entry must be sourced, typed and verified."""
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list) or not raw["entries"]:
        return ["the file needs a non-empty 'entries' list"]
    problems, seen = [], set()
    for position, entry in enumerate(raw["entries"]):
        label = f"entry {position + 1}"
        if not isinstance(entry, dict):
            problems.append(f"{label}: not an object")
            continue
        label = str(entry.get("id", label))
        problems += [f"{label}: missing '{field}'" for field in REQUIRED if not entry.get(field)]
        if entry.get("id") in seen:
            problems.append(f"{label}: duplicate id")
        seen.add(entry.get("id"))
        if entry.get("date_precision") not in PRECISIONS:
            problems.append(f"{label}: date_precision must be one of {sorted(PRECISIONS)}")
        period = str(entry.get("period", ""))
        if entry.get("date_precision") == "day" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
            problems.append(f"{label}: a 'day' period must look like 2026-08-24")
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        problems += [f"{label}: source is missing '{field}'" for field in SOURCE_REQUIRED if field not in source]
        if source.get("type") not in SOURCE_TYPES:
            problems.append(f"{label}: source type must be one of {sorted(SOURCE_TYPES)}")
        if not str(source.get("url", "")).startswith("https://"):
            problems.append(f"{label}: source url must be an https link")
        verified = entry.get("verified") if isinstance(entry.get("verified"), dict) else {}
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(verified.get("on", ""))) or not verified.get("how"):
            problems.append(f"{label}: 'verified' needs a date ('on') and a description ('how')")
        if source.get("type") == "press_report" and "press" not in str(source.get("publisher", "")).lower():
            problems.append(f"{label}: press entries must say 'press' in the publisher so readers can see the confidence level")
    return problems


def load_timeline(path: Path = KNOWLEDGE_PATH) -> list[Entry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_entries(raw)
    if problems:
        raise ValueError("Invalid knowledge file: " + "; ".join(problems))
    entries = [Entry(**{field: item[field] for field in REQUIRED}) for item in raw["entries"]]
    return sorted(entries, key=lambda entry: entry.sort_key)


def date_label(entry: Entry) -> str:
    """'24 Aug 2026', 'Jul 2025', '2023' or 'undated' (never more precise than the source)."""
    if entry.date_precision == "day":
        year, month, day = (int(part) for part in entry.period.split("-"))
        return f"{day} {_MONTHS[month - 1]} {year}"
    if entry.date_precision == "month":
        year, month = (int(part) for part in entry.period.split("-")[:2])
        return f"{_MONTHS[month - 1]} {year}"
    return "undated" if entry.period == "undated" else entry.period


def fact_text(entry: Entry) -> str:
    """One evidence sentence: what was published, by whom, and how reliable the source is."""
    return (f"{entry.what_changed} (Source: {entry.source['publisher']}, {date_label(entry)}; "
            f"{SOURCE_TYPES[entry.source_type]}.)")


def view_count_note(training_period: str) -> str:
    """The caveat that absolute view numbers are not comparable across YouTube's counting changes."""
    return (f"YouTube changed how views are counted on 24 Aug 2026 (from the first frame, all formats) and on 31 Mar 2025 for Shorts, "
            f"while this model learned from {training_period} trending videos, so absolute view numbers may not match today's counts.")


def select_entries(gates: dict[str, bool], entries: list[Entry] | None = None) -> list[Entry]:
    """The few entries that matter for this advice (kept short so a small local model gets a compact prompt)."""
    entries = entries if entries is not None else load_timeline()
    by_id = {entry.id: entry for entry in entries}
    wanted = list(ALWAYS_SHOWN) + ([TIMING_ENTRY] if gates.get("timing") else [])
    return [by_id[ident] for ident in wanted if ident in by_id]


def newest_verification(entries: list[Entry]) -> date:
    return max(date.fromisoformat(entry.verified["on"]) for entry in entries)
