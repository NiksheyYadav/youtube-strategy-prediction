"""Guard rails: no credentials in tracked files, and secret files are git-ignored."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "OpenAI/Anthropic-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "hard-coded secret assignment": re.compile(
        r"""(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*["'][A-Za-z0-9_\-]{24,}["']"""
    ),
}


def _git(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True)


def _tracked_files() -> list[Path]:
    result = _git("ls-files")
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    return [ROOT / name for name in result.stdout.splitlines()]


def test_no_credentials_in_tracked_text_files():
    findings = []
    for path in _tracked_files():
        if not path.is_file() or path.suffix in {".joblib", ".pkl", ".png", ".pptx", ".csv"}:
            continue
        if path.name == "test_no_secrets.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    assert not findings, findings


@pytest.mark.parametrize("name", [".env", ".env.local", ".streamlit/secrets.toml", "llm.key"])
def test_secret_files_are_gitignored(name):
    if _git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("not a git checkout")
    assert _git("check-ignore", "-q", name).returncode == 0, f"{name} is not ignored"
