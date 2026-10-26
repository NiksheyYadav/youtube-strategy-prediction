"""Developer check: run the REAL local-model chain on a golden draft and show what came out.

    python scripts/try_real_model.py [draft_name]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.golden import GOLDEN_DRAFTS  # noqa: E402
from src.inference import load_bundle  # noqa: E402
from src.recommendations import generate_recommendation, resolve_runtime  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "education"
runtime = resolve_runtime()
print(f"device: {runtime.profile.describe()} | main: {runtime.choice.name} | lite: {runtime.fallback}", flush=True)
result = generate_recommendation(load_bundle(), GOLDEN_DRAFTS[name], runtime=runtime)
rec = result.recommendation
print(f"source={result.source} tier={result.tier} model={result.model} seconds={result.seconds:.0f} dropped={result.dropped}")
print("notice:", result.notice)
print("summary:", rec["summary"][:260])
for item in rec["priorities"]:
    print(" priority:", item["action"], "|", item["why"][:110])
print("titles:", [t["title"] for t in rec["title_alternatives"]])
print("tags:", rec["tag_suggestions"]["add"])
print("description:", [d["change"][:90] for d in rec["description_advice"]])
print("rescored by ML:", [(row["kind"], f"{row['views_change_pct']:+.1f}%") for row in result.rescored])
