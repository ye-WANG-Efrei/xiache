"""Evaluator service for skill evolution proposals.

Runs a set of pure-Python checks (no external LLM required) against a
proposed skill and returns an EvaluationResult with a quality score.
"""
from __future__ import annotations

from typing import Optional

from app.schemas.api import EvaluationResult

# Dangerous patterns that must not appear in the skill body.
_DANGEROUS_PATTERNS: list[str] = [
    "rm -rf /",
    "os.system",
    "subprocess.call",
    "eval(",
    "exec(",
    "__import__",
    "DROP TABLE",
    "DELETE FROM",
]


def evaluate_evolution(
    skill_name: str,
    skill_description: str,
    skill_body: str,
    origin: str,
    parent_skill_id: Optional[str],
    change_summary: str,
) -> EvaluationResult:
    """Run all quality checks and return a structured EvaluationResult.

    This function is synchronous — all checks are pure Python with no I/O.
    """
    checks: dict[str, bool] = {}
    failure_reasons: list[str] = []

    # ------------------------------------------------------------------
    # Check 1: has_name
    # ------------------------------------------------------------------
    name_ok = (
        bool(skill_name)
        and len(skill_name) >= 3
        and "/" not in skill_name
        and "\\" not in skill_name
    )
    checks["has_name"] = name_ok
    if not name_ok:
        failure_reasons.append(
            "has_name: skill name must be at least 3 characters and contain no path separators."
        )

    # ------------------------------------------------------------------
    # Check 2: has_description
    # ------------------------------------------------------------------
    desc_ok = bool(skill_description) and len(skill_description) >= 10
    checks["has_description"] = desc_ok
    if not desc_ok:
        failure_reasons.append(
            "has_description: skill description must be at least 10 characters."
        )

    # ------------------------------------------------------------------
    # Check 3: has_body
    # ------------------------------------------------------------------
    body_ok = bool(skill_body) and len(skill_body) >= 20
    checks["has_body"] = body_ok
    if not body_ok:
        failure_reasons.append(
            "has_body: SKILL.md body (after frontmatter) must be at least 20 characters."
        )

    # ------------------------------------------------------------------
    # Check 4: lineage_valid
    # ------------------------------------------------------------------
    if origin in ("fixed", "derived"):
        lineage_ok = parent_skill_id is not None and bool(parent_skill_id)
    else:
        # captured — no parent needed
        lineage_ok = True
    checks["lineage_valid"] = lineage_ok
    if not lineage_ok:
        failure_reasons.append(
            "lineage_valid: origin 'fixed' or 'derived' requires a parent_skill_id."
        )

    # ------------------------------------------------------------------
    # Check 5: change_explained
    # ------------------------------------------------------------------
    if origin in ("fixed", "derived"):
        change_ok = bool(change_summary) and len(change_summary) >= 10
    else:
        change_ok = True
    checks["change_explained"] = change_ok
    if not change_ok:
        failure_reasons.append(
            "change_explained: change_summary must be at least 10 characters for "
            "origin 'fixed' or 'derived'."
        )

    # ------------------------------------------------------------------
    # Check 6: no_dangerous_patterns
    # ------------------------------------------------------------------
    body_lower = skill_body  # keep original case for pattern matching
    dangerous_found = [p for p in _DANGEROUS_PATTERNS if p in body_lower]
    safe_ok = len(dangerous_found) == 0
    checks["no_dangerous_patterns"] = safe_ok
    if not safe_ok:
        failure_reasons.append(
            f"no_dangerous_patterns: forbidden patterns detected: {dangerous_found!r}."
        )

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------
    total = len(checks)
    passed_count = sum(1 for v in checks.values() if v)
    quality_score = passed_count / total if total > 0 else 0.0

    # Overall pass: score >= 0.5 AND has_name AND no_dangerous_patterns
    passed = (
        quality_score >= 0.5
        and checks["has_name"]
        and checks["no_dangerous_patterns"]
    )

    notes = (
        "All checks passed."
        if not failure_reasons
        else " | ".join(failure_reasons)
    )

    return EvaluationResult(
        passed=passed,
        quality_score=round(quality_score, 4),
        notes=notes,
        checks=checks,
    )
