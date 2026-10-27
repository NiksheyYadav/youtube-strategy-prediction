"""Write sample_data/sample_channel.csv: a MADE-UP small channel in the YouTube Studio 'Table data.csv' layout.

    python scripts/make_sample_channel.py

It exists so the "My channel" tab can be demonstrated without any account.  Nothing here is real data.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "sample_data" / "sample_channel.csv"
TITLES = [
    "How I organise my study week", "5 free tools every student should know", "My first month learning Python", "Why I stopped using flashcards",
    "Exam revision plan that actually works", "7 mistakes new programmers make", "A day in my life at college", "How to take better notes fast",
    "Budget laptop for students: honest review", "Is a coding bootcamp worth it?", "3 habits that improved my grades", "Learning SQL in 10 days: what happened",
    "How to stay focused while studying online", "My desk setup under 5000 rupees", "Mock interview: what I got wrong", "Top 10 mistakes in group projects",
    "How I built my portfolio website", "What I wish I knew in first year", "Summer break plan for engineering students", "Python vs Java for beginners",
    "How to prepare for placements", "Weekend vlog: hackathon night", "6 shortcuts for faster typing", "Reading research papers without panic",
    "How I use notes apps to plan my week", "Results day reaction and next steps",
]


def main() -> None:
    rng = np.random.default_rng(7)
    start = pd.Timestamp("2026-01-10")
    rows = []
    for number, title in enumerate(TITLES):
        published = start + pd.Timedelta(days=int(number * 9.5 + rng.integers(0, 3)))
        lift = 0.30 * any(ch.isdigit() for ch in title) + 0.25 * title.lower().startswith("how") + 0.15 * (published.dayofweek >= 5)
        views = int(np.expm1(np.log(2200) + lift + rng.normal(0, 0.45)))
        rows.append([f"SAMPLE{number + 1:05d}", title, published.strftime("%b %d, %Y"), int(rng.integers(240, 900)), views])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Content", "Video title", "Video publish time", "Duration", "Views"])
        writer.writerow(["Total", "", "", "", sum(row[4] for row in rows)])
        writer.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} made-up videos)")


if __name__ == "__main__":
    main()
