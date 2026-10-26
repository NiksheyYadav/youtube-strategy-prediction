"""The keep-warm workflow must ping more often than Render's 15-minute idle timeout."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "keep-warm.yml"


def test_keep_warm_runs_more_often_than_the_idle_timeout_and_can_be_disabled():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    cron = data[True]["schedule"][0]["cron"]  # YAML parses the key `on` as boolean True
    minutes = int(cron.split()[0].split("/")[1])
    assert minutes < 15
    assert "workflow_dispatch" in data[True]
    job = data["jobs"]["ping"]
    assert "KEEP_WARM_ENABLED" in job["if"]
    assert data["permissions"] == {}
