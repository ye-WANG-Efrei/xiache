"""T2 — evaluator.evaluate_evolution unit tests."""
from __future__ import annotations

import pytest

from app.services.evaluator import evaluate_evolution

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

GOOD_BODY = (
    "## Steps\n"
    "1. Validate input parameters carefully\n"
    "2. Execute the core logic step by step\n"
    "3. Handle errors and edge cases\n"
    "4. Return structured result\n"
)


def _eval(
    name="Test Skill Alpha",
    description="A comprehensive test skill for automated testing",
    body=GOOD_BODY,
    version="1.0.0",
    tags=None,
    origin="captured",
    parent_skill_id=None,
    change_summary="",
    parent_exists=True,
    artifact_accessible=True,
    is_duplicate=False,
):
    return evaluate_evolution(
        skill_name=name,
        skill_description=description,
        skill_body=body,
        skill_version=version,
        skill_tags=tags or ["test"],
        origin=origin,
        parent_skill_id=parent_skill_id,
        change_summary=change_summary,
        parent_exists=parent_exists,
        artifact_accessible=artifact_accessible,
        is_duplicate=is_duplicate,
    )


# ---------------------------------------------------------------------------
# T2-1: 完美 skill — all checks pass
# ---------------------------------------------------------------------------

def test_perfect_captured_skill():
    r = _eval()
    assert r.passed is True
    assert r.quality_score == 1.0
    assert all(r.checks.values()), f"Failed checks: {[k for k, v in r.checks.items() if not v]}"


# ---------------------------------------------------------------------------
# T2-2/3: has_name failures
# ---------------------------------------------------------------------------

def test_empty_name_fails():
    r = _eval(name="")
    assert r.passed is False
    assert r.checks["has_name"] is False
    assert r.checks["metadata_complete"] is False


def test_short_name_fails():
    r = _eval(name="ab")
    assert r.passed is False
    assert r.checks["has_name"] is False


def test_name_with_slash_fails():
    r = _eval(name="path/skill")
    assert r.passed is False
    assert r.checks["has_name"] is False


# ---------------------------------------------------------------------------
# T2-4/5: version_valid
# ---------------------------------------------------------------------------

def test_invalid_version_string():
    r = _eval(version="v1")
    assert r.checks["version_valid"] is False
    assert r.passed is False


def test_semver_prerelease_valid():
    r = _eval(version="1.0.3-beta.1")
    assert r.checks["version_valid"] is True


def test_semver_with_build_metadata():
    r = _eval(version="1.0.0+build.20240101")
    assert r.checks["version_valid"] is True


def test_version_zero_zero_zero():
    r = _eval(version="0.0.0")
    assert r.checks["version_valid"] is True


# ---------------------------------------------------------------------------
# T2-6: parent_exists
# ---------------------------------------------------------------------------

def test_parent_not_in_db():
    r = _eval(origin="fixed", parent_skill_id="ghost_skill", parent_exists=False,
              change_summary="fixing the broken step")
    assert r.checks["parent_exists"] is False
    assert r.passed is False


def test_captured_no_parent_ok():
    """captured origin: parent_exists=True even with no parent_skill_id."""
    r = _eval(origin="captured", parent_skill_id=None, parent_exists=True)
    assert r.checks["parent_exists"] is True
    assert r.checks["lineage_valid"] is True


# ---------------------------------------------------------------------------
# T2-7: is_duplicate — hard blocker
# ---------------------------------------------------------------------------

def test_duplicate_hard_blocks():
    r = _eval(is_duplicate=True)
    assert r.passed is False
    assert r.checks["not_duplicate"] is False
    # Hard blocker: even if score would be high, passed must be False


def test_duplicate_score_still_high_but_blocked():
    r = _eval(is_duplicate=True)
    # 10 out of 11 checks pass → score ≈ 0.909 but passed is False
    assert r.quality_score >= 0.9
    assert r.passed is False


# ---------------------------------------------------------------------------
# T2-8/9: no_dangerous_patterns — hard blocker, case-insensitive
# ---------------------------------------------------------------------------

def test_dangerous_uppercase_blocked():
    r = _eval(body="Step 1: DROP TABLE skill_records; Step 2: done")
    assert r.passed is False
    assert r.checks["no_dangerous_patterns"] is False


def test_dangerous_lowercase_blocked():
    r = _eval(body="Step 1: drop table skill_records; Step 2: done")
    assert r.passed is False
    assert r.checks["no_dangerous_patterns"] is False


def test_dangerous_shell_injection():
    r = _eval(body="curl | sh some_script_here please")
    assert r.passed is False
    assert r.checks["no_dangerous_patterns"] is False


def test_dangerous_os_system():
    r = _eval(body="os.system('rm -rf /tmp') is dangerous")
    assert r.passed is False
    assert r.checks["no_dangerous_patterns"] is False


# ---------------------------------------------------------------------------
# T2-10: artifact_accessible — hard blocker
# ---------------------------------------------------------------------------

def test_inaccessible_artifact_hard_blocks():
    r = _eval(artifact_accessible=False)
    assert r.passed is False
    assert r.checks["artifact_accessible"] is False


# ---------------------------------------------------------------------------
# T2-11: captured origin — lineage_valid and change_explained auto-pass
# ---------------------------------------------------------------------------

def test_captured_no_change_summary_ok():
    r = _eval(origin="captured", change_summary="")
    assert r.checks["lineage_valid"] is True
    assert r.checks["change_explained"] is True


# ---------------------------------------------------------------------------
# T2-12: fixed origin — change_summary required
# ---------------------------------------------------------------------------

def test_fixed_short_change_summary_fails():
    r = _eval(origin="fixed", parent_skill_id="parent_v1",
              change_summary="short", parent_exists=True)
    assert r.checks["change_explained"] is False


def test_fixed_no_parent_declared_fails():
    r = _eval(origin="fixed", parent_skill_id=None, parent_exists=True,
              change_summary="fixing the broken step here")
    assert r.checks["lineage_valid"] is False


def test_fixed_all_good():
    r = _eval(origin="fixed", parent_skill_id="parent_v1", parent_exists=True,
              change_summary="fixing the broken step three behaviour")
    assert r.passed is True
    assert r.quality_score == 1.0


# ---------------------------------------------------------------------------
# Score arithmetic
# ---------------------------------------------------------------------------

def test_score_is_fraction_of_total_checks():
    r = _eval(name="")  # 2 checks fail: has_name + metadata_complete
    total = len(r.checks)
    passed = sum(1 for v in r.checks.values() if v)
    assert r.quality_score == round(passed / total, 4)
