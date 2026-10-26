"""Small text helpers for safely displaying model-written text."""

from __future__ import annotations

import re

_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-!|>~$<])")


def escape_markdown(value: object) -> str:
    """Escape Markdown so text written by a language model is shown as plain text."""
    return _SPECIAL.sub(r"\\\1", str(value))
