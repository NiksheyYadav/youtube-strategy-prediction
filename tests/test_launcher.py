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


def _fake_manifest(models_dir: Path, *parts: str) -> None:
    path = models_dir.joinpath("manifests", "registry.ollama.ai", *parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")


def test_models_on_disk_are_found_without_a_running_server(tmp_path):
    _fake_manifest(tmp_path, "library", "qwen2.5", "3b")
    _fake_manifest(tmp_path, "library", "qwen2.5", "0.5b")
    _fake_manifest(tmp_path, "someone", "my-model", "latest")
    assert launch.models_on_disk([tmp_path]) == ["qwen2.5:0.5b", "qwen2.5:3b", "someone/my-model:latest"]
    assert launch.models_on_disk([tmp_path / "missing"]) == []


def test_known_models_prefers_the_server_and_falls_back_to_disk(monkeypatch, tmp_path):
    _fake_manifest(tmp_path, "library", "qwen2.5", "3b")
    monkeypatch.setattr(launch, "ollama_models_dirs", lambda: [tmp_path])
    monkeypatch.setattr(launch, "installed_models", lambda: ["from-server:1b"])
    assert launch.known_models() == ["from-server:1b"]
    monkeypatch.setattr(launch, "installed_models", lambda: None)
    assert launch.known_models() == ["qwen2.5:3b"]
    assert launch.missing_models(["qwen2.5:3b", "qwen2.5:0.5b"], launch.known_models()) == ["qwen2.5:0.5b"]


def test_model_override_replaces_the_automatic_choice_but_keeps_the_lite_fallback():
    cpu = DeviceProfile(15.7, 16)
    assert launch.model_plan(cpu, "qwen2.5:7b") == ["qwen2.5:7b", "qwen2.5:0.5b"]
    assert launch.model_plan(cpu, "qwen2.5:0.5b") == ["qwen2.5:0.5b"]
    assert "qwen2.5:7b" in launch.catalog_names()


def test_unknown_model_is_rejected_before_anything_is_changed():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "launch.py"), "--model", "not-a-model"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2
    assert "Unknown model" in result.stderr


def test_smoke_test_checks_that_the_model_really_answers(monkeypatch):
    class Reply:
        def __init__(self, text):
            self.text = text

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, *args):
            return ('{"response": "%s"}' % self.text).encode()

    monkeypatch.setattr(launch.urllib.request, "urlopen", lambda *a, **k: Reply("OK"))
    assert launch.smoke_test("qwen2.5:3b") is True
    monkeypatch.setattr(launch.urllib.request, "urlopen", lambda *a, **k: Reply("   "))
    assert launch.smoke_test("qwen2.5:3b") is False

    def refuse(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(launch.urllib.request, "urlopen", refuse)
    assert launch.smoke_test("qwen2.5:3b") is False


def test_check_reports_models_already_on_disk_instead_of_asking_to_download_them(monkeypatch, tmp_path, capsys):
    _fake_manifest(tmp_path, "library", "qwen2.5", "3b")
    _fake_manifest(tmp_path, "library", "qwen2.5", "0.5b")
    monkeypatch.setattr(launch, "ollama_models_dirs", lambda: [tmp_path])
    monkeypatch.setattr(launch, "installed_models", lambda: None)  # server not running
    monkeypatch.setattr(launch, "detect_device", lambda: DeviceProfile(15.7, 16))
    launch.check()
    output = capsys.readouterr().out
    assert "Models present: qwen2.5:0.5b, qwen2.5:3b" in output
    assert "To download   : nothing" in output


def test_wrappers_exist_and_shell_script_is_executable_text():
    for name in ("run.ps1", "run.sh", "run.bat", "run_demo.ps1"):
        assert (ROOT / name).exists(), name
    assert (ROOT / "run.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")
