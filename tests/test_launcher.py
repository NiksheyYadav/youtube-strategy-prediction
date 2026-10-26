"""The cross-device launcher: planning logic and a read-only --check run."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from src.device_profile import DeviceProfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("launch", ROOT / "scripts" / "launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


@pytest.mark.parametrize("profile, expected", [
    (DeviceProfile(16, 16, "NVIDIA GeForce RTX 5050 Laptop GPU", 8.0), ["qwen2.5:7b", "qwen2.5:0.5b"]),
    (DeviceProfile(15.7, 16), ["qwen2.5:3b", "qwen2.5:0.5b"]),
    (DeviceProfile(8, 8), ["qwen2.5:1.5b", "qwen2.5:0.5b"]),
    (DeviceProfile(4, 4), []),
])
def test_model_plan_fits_the_device_and_always_includes_the_lite_fallback(profile, expected):
    assert launch.model_plan(profile) == expected


def test_missing_models_uses_prefix_matching():
    assert launch.missing_models(["qwen2.5:3b", "qwen2.5:0.5b"], ["qwen2.5:3b-instruct-q4_K_M"]) == ["qwen2.5:0.5b"]
    assert launch.missing_models(["qwen2.5:3b"], []) == ["qwen2.5:3b"]
    assert launch.missing_models([], ["anything"]) == []


def test_requirements_hash_changes_with_content_and_candidates_are_paths():
    assert len(launch.requirements_hash()) == 64
    assert all(isinstance(p, Path) for p in launch.ollama_candidates())


def test_check_mode_changes_nothing_and_reports_the_plan():
    before = (launch.VENV.exists(), launch.MARKER.exists() if launch.VENV.exists() else None)
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "launch.py"), "--check"], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    for label in ("Python", "Environment", "Device", "Model plan", "Ollama", "nothing was changed"):
        assert label in result.stdout
    assert before == (launch.VENV.exists(), launch.MARKER.exists() if launch.VENV.exists() else None)


def test_wrappers_exist_and_shell_script_is_executable_text():
    for name in ("run.ps1", "run.sh", "run.bat", "run_demo.ps1"):
        assert (ROOT / name).exists(), name
    assert (ROOT / "run.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")
