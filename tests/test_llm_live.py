"""Optional live check against a REAL local model. Skipped unless explicitly enabled:

    $env:RUN_LIVE_LLM_TESTS = "1"; python -m pytest tests/test_llm_live.py -q -s

Needs a running local server (e.g. Ollama) with a model suited to this device. Makes no online calls.
"""

from __future__ import annotations

import os

import pytest

from src.golden import GOLDEN_DRAFTS
from src.inference import load_bundle
from src.recommendations import generate_recommendation, resolve_runtime
from src.reco_schema import validate_recommendation

pytestmark = pytest.mark.live


@pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM_TESTS") != "1", reason="set RUN_LIVE_LLM_TESTS=1 to run against a local model")
def test_real_local_model_returns_a_valid_evidence_checked_recommendation():
    runtime = resolve_runtime()
    if not runtime.ready:
        pytest.skip(f"no usable local model: {runtime.choice.reason}")
    bundle = load_bundle()
    result = generate_recommendation(bundle, GOLDEN_DRAFTS["education"], runtime=runtime)
    print(f"\nsource={result.source} model={result.model} seconds={result.seconds:.0f} notice={result.notice}")
    assert validate_recommendation(result.recommendation, result.packet) == []
    assert result.forecast.expected_views > 0
