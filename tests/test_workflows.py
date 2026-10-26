"""The keep-warm workflow must ping more often than Render's 15-minute idle timeout."""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "keep-warm.yml"


def test_keep_warm_runs_more_often_than_the_idle_timeout_and_can_be_disabled():
    text = WORKFLOW.read_text(encoding="utf-8")
    cron = re.search(r'cron:\s*"\d+-59/(\d+) \* \* \* \*"', text)
    assert cron and int(cron.group(1)) < 15
    assert "workflow_dispatch:" in text
    assert "vars.KEEP_WARM_ENABLED != 'false'" in text
    assert re.search(r"^permissions:\s*\{\}\s*$", text, re.MULTILINE)
