"""Golden snapshot of the ML layer's numerical outputs.

The recommendation layer must never change a forecast.  ``collect_snapshot`` runs the
existing prediction and insight functions on fixed drafts; ``tests/test_golden_predictions.py``
compares the result with ``tests/fixtures/golden_predictions.json``, which was recorded from the
code *before* the recommendation layer existed.

Record (only when the ML layer is intentionally changed):  python -m src.golden --record
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.inference import load_bundle, predict_video
from src.insights import Draft, category_what_if, explain_groups, forecast_percentile, suggest_edits, time_grid

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden_predictions.json"

GOLDEN_DRAFTS: dict[str, Draft] = {
    "education": Draft("5 Study Tips That Actually Work for Students", "study tips, productivity, student life, exam preparation",
                       "A practical guide for students who want a repeatable study routine. Share your own routine in the comments.",
                       "Education", 5, 18),
    "music": Draft("Neon Nights (Official Music Video)", "new song, official video, music video, hindi song",
                   "Official music video. Stream the song everywhere. Subscribe for new releases. https://example.com/stream",
                   "Music", 4, 17),
    "tech": Draft("5 Things I Wish I Knew Before Buying This Phone", "phone review, smartphone, tech review, buying guide",
                  "An honest review after 30 days of use. Which features matter and which are marketing? #review #tech",
                  "Science & Technology", 2, 19),
    "trailer": Draft("Official Trailer | Releasing This Friday", "trailer, official trailer, movie, new movie",
                     "Watch the official trailer. In cinemas this Friday. #trailer #movie", "Entertainment", 0, 12),
    "no_tags_short": Draft("Hi", "", "", "Comedy", 6, 3),
    "long_caps": Draft("THIS IS AN EXTREMELY LONG TITLE " * 3, "a|b|c", "x" * 3000, "News & Politics", 1, 23),
    "non_ascii": Draft("पढ़ाई के 5 आसान तरीके", "पढ़ाई, परीक्षा", "छात्रों के लिए गाइड", "Education", 3, 9),
}


def _round(value: float | None, digits: int = 10) -> float | None:
    return None if value is None else round(float(value), digits)


def collect_snapshot(bundle: dict[str, object] | None = None) -> dict[str, object]:
    bundle = bundle or load_bundle()
    snapshot: dict[str, object] = {}
    for name, draft in GOLDEN_DRAFTS.items():
        prediction = predict_video(
            bundle, title=draft.title, tags=draft.tags, description=draft.description,
            category_name=draft.category_name, day_of_week=draft.day_of_week, publish_hour=draft.publish_hour,
        )
        explanation = explain_groups(bundle, draft)
        grid = time_grid(bundle, draft)
        percentiles = forecast_percentile(bundle, draft.category_name, prediction.views_log, prediction.engagement_rate)
        snapshot[name] = {
            "prediction": {
                "expected_views": _round(prediction.expected_views),
                "views_log": _round(prediction.views_log),
                "views_ci_low": _round(prediction.views_ci_low),
                "views_ci_high": _round(prediction.views_ci_high),
                "views_tree_low": _round(prediction.views_low),
                "views_tree_high": _round(prediction.views_high),
                "engagement_rate": _round(prediction.engagement_rate),
                "engagement_ci_low": _round(prediction.engagement_ci_low),
                "engagement_ci_high": _round(prediction.engagement_ci_high),
                "out_of_range_features": sorted(prediction.out_of_range_features),
            },
            "percentiles": {key: (_round(value) if isinstance(value, float) else value) for key, value in percentiles.items()},
            "shapley": {
                "baseline_views": _round(explanation.baseline_views),
                "forecast_views": _round(explanation.forecast_views),
                "effects": {
                    row.group: [_round(row.views_multiplier), _round(row.engagement_effect_pp)]
                    for row in explanation.table.itertuples()
                },
            },
            "best_slots": [
                [str(row.day_name), int(row.hour), _round(row.views)] for row in grid.best_slots.itertuples()
            ],
            "top_edits": [
                [item.key, _round(item.views_change_pct), _round(item.engagement_change_pp)]
                for item in suggest_edits(bundle, draft)[:5]
            ],
            "category_top3": [
                [row.category, _round(row.views)] for row in category_what_if(bundle, draft).head(3).itertuples()
            ],
        }
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="Overwrite the golden fixture with current outputs.")
    arguments = parser.parse_args()
    if not arguments.record:
        parser.error("Pass --record to (re)write the golden fixture.")
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(collect_snapshot(), indent=1, sort_keys=True), encoding="utf-8")
    print(f"Recorded {len(GOLDEN_DRAFTS)} drafts to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
