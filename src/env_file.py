"""Read a local ``.env`` file into the process environment (standard library only).

``.env`` is git-ignored and is where optional settings live (LLM model, Google sign-in client).  Values that are
already set in the real environment always win, so a deployment (for example Render) can override the file.
Values are never printed or logged here.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import MutableMapping

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_env_text(text: str) -> dict[str, str]:
    """``KEY=value`` lines; ``#`` comments, blank lines, an optional ``export`` and matching quotes are handled."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not _KEY.match(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:  # trailing comment on an unquoted value
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def load_env_file(path: Path = ENV_PATH, environ: MutableMapping[str, str] | None = None) -> list[str]:
    """Copy settings from ``path`` into ``environ`` without overriding existing ones; returns the names that were set."""
    environ = os.environ if environ is None else environ
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    applied = []
    for key, value in parse_env_text(text).items():
        if key not in environ and value != "":
            environ[key] = value
            applied.append(key)
    return applied
