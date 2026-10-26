"""Run the real local-model chain on the example drafts and record what happened (for the report).

    python scripts/eval_ai_coach.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.golden import GOLDEN_DRAFTS  # noqa: E402
from src.inference import load_bundle  # noqa: E402
from src.recommendations import generate_recommendation, resolve_runtime  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "deliverables" / "assets" / "ai_coach_runs.json"
runtime = resolve_runtime()
bundle = load_bundle()
runs = []
for name in ("education", "music", "tech", "trailer"):
    result = generate_recommendation(bundle, GOLDEN_DRAFTS[name], runtime=runtime)
    row = {"draft": name, "source": result.source, "tier": result.tier, "model": result.model, "seconds": round(result.seconds),
           "dropped": result.dropped, "titles": [t["title"] for t in result.recommendation["title_alternatives"]],
           "rescored": [round(r["views_change_pct"], 1) for r in result.rescored if r["kind"] == "title"],
           "notice": result.notice}
    runs.append(row)
    print(row, flush=True)
    OUT.write_text(json.dumps({"device": runtime.profile.describe(), "main": runtime.choice.name, "lite": runtime.fallback, "runs": runs}, indent=1), encoding="utf-8")
