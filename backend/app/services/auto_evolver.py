"""Auto-evolution service.

When a skill's quality counters cross configured thresholds, this service:
  1. Loads the skill's current SKILL.md from its artifact
  2. Calls an LLM with the failure notes to generate an improved SKILL.md
  3. Packages the result into a new ZIP artifact
  4. Persists the artifact and creates a SkillEvolution record (status=pending)

The evolution still goes through the normal evaluator — it's not auto-accepted
unless the evaluator score crosses AUTO_ACCEPT_THRESHOLD.
"""
from __future__ import annotations

import hashlib
import io
import logging
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.models.db import Artifact, SkillEvolution, SkillRecord
from app.services.skill_parser import parse_skill_md

logger = logging.getLogger(__name__)

_IMPROVE_PROMPT = """\
You are a skill-improvement assistant for an AI agent skill registry.

<current_skill_md>
{skill_md}
</current_skill_md>

<execution_failure_notes>
{failure_notes}
</execution_failure_notes>

Task: Rewrite the SKILL.md to fix the issues described in the failure notes above.
- Keep the YAML frontmatter (name, description, version, tags, input_schema, output_schema).
- Bump the patch version (e.g. 1.0.0 → 1.0.1).
- Improve the body so agents can follow it without falling back.
- Output ONLY the new SKILL.md text, no commentary, no markdown fences.
"""

_MAX_NOTE_LEN = 500  # characters per note — guards against prompt injection


def _sanitize_notes(notes: list[str]) -> list[str]:
    # Escape first, then truncate — prevents truncation mid-tag leaving a dangling "</"
    return [n.replace("</", "<\\/")[:_MAX_NOTE_LEN] for n in notes]


def _bump_patch(version: str) -> str:
    """Increment patch number: 1.2.3 → 1.2.4, handles pre-release like 1.0.3-beta.1."""
    parts = version.split(".")
    if len(parts) >= 3:
        # Strip pre-release (-beta.1) AND build metadata (+build.1) before parsing digits
        patch_numeric = parts[2].split("-")[0].split("+")[0]
        if patch_numeric.isdigit():
            parts[2] = str(int(patch_numeric) + 1)
            return ".".join(parts[:3])  # drop pre-release suffix in bumped version
    return version + ".1"


def _make_zip(skill_md_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SKILL.md", skill_md_text.encode("utf-8"))
    return buf.getvalue()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _call_llm(prompt: str) -> Optional[str]:
    settings = get_settings()
    if not settings.LLM_API_KEY:
        logger.warning("auto_evolver: LLM_API_KEY not set, skipping LLM rewrite")
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
        )
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("auto_evolver: LLM call failed: %s", exc)
        return None


async def maybe_evolve(
    skill: SkillRecord,
    failure_notes: list[str],
    db: AsyncSession,
    triggered_by: str = "auto_evolver",
) -> Optional[str]:
    """Attempt to auto-evolve *skill* based on *failure_notes*.

    Returns the new evolution_id if an evolution was created, else None.
    """
    settings = get_settings()

    # Load current SKILL.md
    try:
        zip_bytes = await storage.load_artifact(skill.artifact_id)
    except Exception as exc:
        logger.warning("auto_evolver: cannot load artifact for %s: %s", skill.id, exc)
        return None

    meta = parse_skill_md(zip_bytes)
    current_skill_md = _extract_raw_skill_md(zip_bytes)
    if not current_skill_md:
        logger.warning("auto_evolver: no SKILL.md in artifact for %s", skill.id)
        return None

    # Guard: skip if there is already a pending/evaluating evolution for this skill
    pending_check = await db.execute(
        select(SkillEvolution).where(
            SkillEvolution.parent_skill_id == skill.id,
            SkillEvolution.status.in_(["pending", "evaluating"]),
        )
    )
    if pending_check.scalar_one_or_none() is not None:
        logger.info(
            "auto_evolver: skill %s already has a pending evolution, skipping", skill.id
        )
        return None

    # Build prompt and call LLM (sanitize notes to prevent prompt injection)
    safe_notes = _sanitize_notes(failure_notes)
    notes_text = "\n".join(f"- {n}" for n in safe_notes) if safe_notes else "(no notes)"
    prompt = _IMPROVE_PROMPT.format(
        skill_md=current_skill_md,
        failure_notes=notes_text,
    )
    new_skill_md = await _call_llm(prompt)
    if not new_skill_md or len(new_skill_md.strip()) < 50:
        logger.warning("auto_evolver: LLM returned empty/short result for %s", skill.id)
        return None

    # Package into ZIP artifact
    zip_bytes_new = _make_zip(new_skill_md)
    fingerprint = _sha256(zip_bytes_new)

    # Dedup — skip if fingerprint already exists as an accepted SkillRecord
    existing = await db.execute(
        select(SkillRecord).where(SkillRecord.content_fingerprint == fingerprint)
    )
    if existing.scalar_one_or_none():
        logger.info("auto_evolver: fingerprint already exists for %s, skipping", skill.id)
        return None

    # Write DB rows first, then persist to filesystem.
    # If storage.save_artifact fails, the DB transaction rolls back cleanly.
    artifact_id = str(uuid.uuid4())

    artifact = Artifact(
        id=artifact_id,
        file_count=1,
        file_names=["SKILL.md"],
        content_fingerprint=fingerprint,
        created_at=datetime.now(timezone.utc),
        created_by=triggered_by,
    )
    db.add(artifact)
    await db.flush()  # artifact row confirmed in DB before touching filesystem

    # Persist to storage — if this fails the DB transaction will roll back
    await storage.save_artifact(artifact_id, zip_bytes_new)

    # Derive candidate skill_id
    new_version = _bump_patch(meta.get("version", "1.0.0"))
    candidate_id = f"{skill.id}_auto_{new_version.replace('.', '_')}"

    safe_summary_notes = _sanitize_notes(failure_notes[:3])
    change_summary = (
        f"Auto-evolved from {skill.id} based on execution quality metrics. "
        f"Failure notes: {'; '.join(safe_summary_notes)}"
    )

    evo = SkillEvolution(
        id=str(uuid.uuid4()),
        artifact_id=artifact_id,
        parent_skill_id=skill.id,
        candidate_skill_id=candidate_id,
        origin="fixed",
        status="pending",
        proposed_name=meta.get("name", skill.name),
        proposed_desc=meta.get("description", skill.description),
        change_summary=change_summary,
        proposed_by=triggered_by,
        tags=meta.get("tags", skill.tags),
        proposed_at=datetime.now(timezone.utc),
        evaluation_notes="Auto-generated by auto_evolver. Awaiting evaluator.",
        auto_accepted=False,
    )
    db.add(evo)
    await db.flush()

    logger.info(
        "auto_evolver: created evolution %s for skill %s (candidate=%s)",
        evo.id, skill.id, candidate_id,
    )
    return evo.id


def _extract_raw_skill_md(zip_bytes: bytes) -> Optional[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            skill_name = next(
                (n for n in names if n.split("/")[-1] == "SKILL.md"), None
            )
            if skill_name is None:
                return None
            return zf.read(skill_name).decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        return None


def should_evolve(skill: SkillRecord) -> tuple[bool, str]:
    """Return (True, reason) if skill's quality metrics cross thresholds."""
    settings = get_settings()

    if skill.total_selections < settings.AUTOEVO_MIN_SELECTIONS:
        return False, "not enough data"

    fallback_rate = skill.total_fallbacks / skill.total_selections
    if fallback_rate > settings.AUTOEVO_FALLBACK_RATE:
        return True, f"fallback_rate={fallback_rate:.2f} > {settings.AUTOEVO_FALLBACK_RATE}"

    if skill.total_applied > 0:
        completion_rate = skill.total_completions / skill.total_applied
        if completion_rate < settings.AUTOEVO_COMPLETION_RATE:
            return True, f"completion_rate={completion_rate:.2f} < {settings.AUTOEVO_COMPLETION_RATE}"

    return False, "metrics OK"
