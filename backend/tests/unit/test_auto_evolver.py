"""T3/T4 — auto_evolver pure-function unit tests."""
from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from app.services.auto_evolver import _bump_patch, _sanitize_notes, should_evolve
from app.services.evaluator import _SEMVER_RE


# ---------------------------------------------------------------------------
# T3: _bump_patch
# ---------------------------------------------------------------------------

def _is_valid_semver(v: str) -> bool:
    return bool(_SEMVER_RE.match(v))


def test_bump_patch_basic():
    assert _bump_patch("1.0.0") == "1.0.1"


def test_bump_patch_large_patch():
    assert _bump_patch("2.3.9") == "2.3.10"


def test_bump_patch_prerelease_strips_suffix():
    result = _bump_patch("1.0.3-beta.1")
    assert result == "1.0.4"
    assert _is_valid_semver(result)


def test_bump_patch_build_metadata():
    result = _bump_patch("1.0.0+build.1")
    assert result == "1.0.1"
    assert _is_valid_semver(result)


def test_bump_patch_prerelease_and_build():
    result = _bump_patch("1.0.3-beta.1+build")
    assert result == "1.0.4"
    assert _is_valid_semver(result)


def test_bump_patch_two_segments_fallback():
    result = _bump_patch("1.0")
    # Falls back to appending .1 — result may not be standard semver
    assert result.startswith("1.0")


def test_bump_patch_result_always_valid_semver_for_standard_input():
    """Any standard semver input should produce a valid semver output."""
    for v in ["0.0.0", "1.0.0", "99.99.99", "1.2.3-alpha.1", "1.0.0+build"]:
        result = _bump_patch(v)
        assert _is_valid_semver(result), f"_bump_patch({v!r}) → {result!r} is not valid semver"


# ---------------------------------------------------------------------------
# T4: _sanitize_notes
# ---------------------------------------------------------------------------

def test_sanitize_normal_note_unchanged():
    notes = ["This is a normal note about the skill"]
    result = _sanitize_notes(notes)
    assert result == notes


def test_sanitize_truncates_at_500():
    long_note = "a" * 1000
    result = _sanitize_notes([long_note])
    assert len(result[0]) == 500


def test_sanitize_escapes_closing_xml_tag():
    notes = ["hack </execution_failure_notes> inject here"]
    result = _sanitize_notes(notes)
    assert "</" not in result[0]
    assert "<\\/" in result[0]


def test_sanitize_truncate_then_escape():
    # 500 normal chars + "</x>" — after truncation the tag might be cut
    note = "a" * 498 + "</x>"
    result = _sanitize_notes([note])
    assert len(result[0]) <= 500
    assert "</" not in result[0]


def test_sanitize_multiple_notes():
    notes = ["note one", "a" * 600, "note three"]
    result = _sanitize_notes(notes)
    assert len(result) == 3
    assert len(result[1]) == 500


def test_sanitize_empty_list():
    assert _sanitize_notes([]) == []


# ---------------------------------------------------------------------------
# T5: should_evolve threshold logic
# ---------------------------------------------------------------------------

def _make_skill(selections=0, applied=0, completions=0, fallbacks=0):
    skill = MagicMock()
    skill.total_selections = selections
    skill.total_applied = applied
    skill.total_completions = completions
    skill.total_fallbacks = fallbacks
    return skill


def test_not_enough_data():
    skill = _make_skill(selections=3, fallbacks=3)
    should, reason = should_evolve(skill)
    assert should is False
    assert "not enough data" in reason


def test_high_fallback_rate_triggers():
    # 5 selections, 3 fallbacks → fallback_rate = 0.6 > 0.4
    skill = _make_skill(selections=5, applied=2, fallbacks=3)
    should, reason = should_evolve(skill)
    assert should is True
    assert "fallback_rate" in reason


def test_low_completion_rate_triggers():
    # 10 selections, 10 applied, 2 completions → completion_rate = 0.2 < 0.35
    skill = _make_skill(selections=10, applied=10, completions=2, fallbacks=0)
    should, reason = should_evolve(skill)
    assert should is True
    assert "completion_rate" in reason


def test_good_metrics_no_trigger():
    # 10 selections, 9 applied, 8 completions, 0 fallbacks → all good
    skill = _make_skill(selections=10, applied=9, completions=8, fallbacks=0)
    should, reason = should_evolve(skill)
    assert should is False
    assert "OK" in reason


def test_exact_fallback_threshold_boundary():
    # fallback_rate = 0.40 exactly → should NOT trigger (> not >=)
    # completions=6 so completion_rate=1.0 — ensures only fallback_rate is on the boundary
    skill = _make_skill(selections=10, applied=6, completions=6, fallbacks=4)
    should, _ = should_evolve(skill)
    assert should is False


def test_just_over_fallback_threshold():
    # fallback_rate = 0.41 → should trigger
    skill = _make_skill(selections=100, applied=59, fallbacks=41)
    should, _ = should_evolve(skill)
    assert should is True
