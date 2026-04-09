"""Evaluator service for skill evolution proposals.

Checks are split into two tiers:
  - Pure checks: run on parsed SKILL.md content with no I/O
  - Context checks: results pre-computed by the caller (require DB / storage)

The caller (evolutions.py) is responsible for the async lookups and passes
results as plain booleans so this module stays synchronous and testable.
"""
from __future__ import annotations

import re
from typing import Optional

from app.schemas.api import EvaluationResult

# Semver: 1.2.3 or 1.2.3-beta.1 or 1.2.3+build
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([\w\-]+(?:\.[\w\-]+)*))?(?:\+([\w\-]+(?:\.[\w\-]+)*))?$"
)

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
    # --- parsed from SKILL.md ---
    skill_name: str,
    skill_description: str,
    skill_body: str,
    skill_version: str,
    skill_tags: list[str],
    # --- from request ---
    origin: str,
    parent_skill_id: Optional[str],
    change_summary: str,
    # --- pre-computed by caller (async DB / storage checks) ---
    parent_exists: bool,       # True if parent_skill_id is None OR parent found in DB
    artifact_accessible: bool, # True if zip was loaded successfully
    is_duplicate: bool,        # True if content fingerprint already in skill_records
) -> EvaluationResult:
    """Run all quality checks and return a structured EvaluationResult."""
    checks: dict[str, bool] = {}
    failure_reasons: list[str] = []

    # ------------------------------------------------------------------
    # 1. metadata_complete — name, description, version, ≥1 tag all present
    # ------------------------------------------------------------------
    metadata_ok = (
        bool(skill_name)
        and bool(skill_description)
        and bool(skill_version)
        and len(skill_tags) > 0
    )
    checks["metadata_complete"] = metadata_ok
    if not metadata_ok:
        missing = []
        if not skill_name:        missing.append("name")
        if not skill_description: missing.append("description")
        if not skill_version:     missing.append("version")
        if not skill_tags:        missing.append("tags (need ≥1)")
        failure_reasons.append(f"metadata_complete: missing fields: {missing}")

    # ------------------------------------------------------------------
    # 2. has_name — name quality
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
            "has_name: name must be ≥3 chars with no path separators."
        )

    # ------------------------------------------------------------------
    # 3. has_description — description quality
    # ------------------------------------------------------------------
    desc_ok = bool(skill_description) and len(skill_description) >= 10
    checks["has_description"] = desc_ok
    if not desc_ok:
        failure_reasons.append("has_description: description must be ≥10 chars.")

    # ------------------------------------------------------------------
    # 4. version_valid — must match semver x.y.z[prerelease][build]
    # ------------------------------------------------------------------
    version_ok = bool(skill_version) and bool(_SEMVER_RE.match(skill_version))
    checks["version_valid"] = version_ok
    if not version_ok:
        failure_reasons.append(
            f"version_valid: {skill_version!r} is not valid semver (expected x.y.z)."
        )

    # ------------------------------------------------------------------
    # 5. has_body — body content present
    # ------------------------------------------------------------------
    body_ok = bool(skill_body) and len(skill_body) >= 20
    checks["has_body"] = body_ok
    if not body_ok:
        failure_reasons.append(
            "has_body: SKILL.md body must be ≥20 chars after frontmatter."
        )

    # ------------------------------------------------------------------
    # 6. parent_exists — parent is in DB (or not required)
    # ------------------------------------------------------------------
    checks["parent_exists"] = parent_exists
    if not parent_exists:
        failure_reasons.append(
            f"parent_exists: parent skill {parent_skill_id!r} not found in registry."
        )

    # ------------------------------------------------------------------
    # 7. lineage_valid — derived/fixed must declare a parent
    # ------------------------------------------------------------------
    if origin in ("fixed", "derived"):
        lineage_ok = parent_skill_id is not None and bool(parent_skill_id)
    else:
        lineage_ok = True
    checks["lineage_valid"] = lineage_ok
    if not lineage_ok:
        failure_reasons.append(
            "lineage_valid: origin 'fixed' or 'derived' requires a parent_skill_id."
        )

    # ------------------------------------------------------------------
    # 8. change_explained — derived/fixed must explain the change
    # ------------------------------------------------------------------
    if origin in ("fixed", "derived"):
        change_ok = bool(change_summary) and len(change_summary) >= 10
    else:
        change_ok = True
    checks["change_explained"] = change_ok
    if not change_ok:
        failure_reasons.append(
            "change_explained: change_summary must be ≥10 chars for derived/fixed skills."
        )

    # ------------------------------------------------------------------
    # 9. not_duplicate — content fingerprint must be new
    # ------------------------------------------------------------------
    checks["not_duplicate"] = not is_duplicate
    if is_duplicate:
        failure_reasons.append(
            "not_duplicate: identical content fingerprint already exists in the registry."
        )

    # ------------------------------------------------------------------
    # 10. artifact_accessible — zip must be readable from storage
    # ------------------------------------------------------------------
    checks["artifact_accessible"] = artifact_accessible
    if not artifact_accessible:
        failure_reasons.append(
            "artifact_accessible: artifact could not be loaded from storage."
        )

    # ------------------------------------------------------------------
    # 11. no_dangerous_patterns — block destructive code
    # ------------------------------------------------------------------
    dangerous_found = [p for p in _DANGEROUS_PATTERNS if p in skill_body]
    safe_ok = len(dangerous_found) == 0
    checks["no_dangerous_patterns"] = safe_ok
    if not safe_ok:
        failure_reasons.append(
            f"no_dangerous_patterns: forbidden patterns detected: {dangerous_found!r}."
        )

    # ------------------------------------------------------------------
    # Aggregate score and overall pass
    # ------------------------------------------------------------------
    total = len(checks)
    passed_count = sum(1 for v in checks.values() if v)
    quality_score = round(passed_count / total, 4) if total > 0 else 0.0

    # Hard blockers — any one of these alone causes rejection
    hard_fail = (
        not checks["has_name"]
        or not checks["no_dangerous_patterns"]
        or not checks["artifact_accessible"]
        or is_duplicate
    )
    passed = quality_score >= 0.5 and not hard_fail

    notes = (
        "All checks passed."
        if not failure_reasons
        else " | ".join(failure_reasons)
    )

    return EvaluationResult(
        passed=passed,
        quality_score=quality_score,
        notes=notes,
        checks=checks,
    )
