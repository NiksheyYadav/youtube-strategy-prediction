"""The recommendation layer must not change any forecast produced by the ML layer."""

from __future__ import annotations

import json

import pytest

from src.golden import FIXTURE_PATH, collect_snapshot


def _assert_close(actual, expected, path=""):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), f"keys differ at {path}"
        for key in expected:
            _assert_close(actual[key], expected[key], f"{path}/{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), f"length differs at {path}"
        for index, (a, e) in enumerate(zip(actual, expected)):
            _assert_close(a, e, f"{path}[{index}]")
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-6, abs=1e-9), f"{path}: {actual} != {expected}"
    else:
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"


def test_numerical_outputs_match_the_recorded_golden_snapshot():
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(collect_snapshot()))
    _assert_close(actual, expected)
