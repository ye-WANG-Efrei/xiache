"""Auto-evolution service.

When a skill's quality counters cross configured thresholds, this service:
  1. Reads the skill's current body text from the DB
  2. Calls an LLM with the failure notes to generate an improved body
  3. Creates a SkillEvolution record (status=pending) with the new body

The evolution still goes through the normal evaluator — it's not auto-accepted
unless the evaluator score crosses AUTO_ACCEPT_THRESHOLD.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.db import SkillEvolution, SkillRecord

logger = logging.getLogger(__name__)

_IMPROVE_PROMPT = """\
You are a skill-improvement assistant for an AI agent skill registry.

<current_skill>
name: {name}
description: {description}

{body}
</current_skill>

<execution_failure_notes>
{failure_notes}
</execution_failure_notes>

Task: Rewrite the skill body (Markdown) to fix the issues described in the failure notes.
- Keep the same name and description unless a fix requires changing them.
- Improve the instructions so agents can follow them without falling back.
- Output ONLY the new body text (no YAML frontmatter, no commentary, no markdown fences).
"""

_MAX_NOTE_LEN = 500  # characters per note — guards against prompt injection


def _sanitize_notes(notes: list[str]) -> list[str]:
    return [n.replace("</", "<\\/")[:_MAX_NOTE_LEN] for n in notes]


def _bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) >= 3:
        patch_numeric = parts[2].split("-")[0].split("+")[0]
        if patch_numeric.isdigit():
            parts[2] = str(int(patch_numeric) + 1)
            return ".".join(parts[:3])
    return version + ".1"


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
    # Guard: skip if there is already a pending/evaluating evolution for this skill
    pending_check = await db.execute(
        select(SkillEvolution).where(
            SkillEvolution.parent_skill_id == skill.slug,
            SkillEvolution.status.in_(["pending", "evaluating"]),
        )
    )
    if pending_check.scalar_one_or_none() is not None:
        logger.info("auto_evolver: skill %s already has a pending evolution, skipping", skill.id)
        return None

    safe_notes = _sanitize_notes(failure_notes)
    notes_text = "\n".join(f"- {n}" for n in safe_notes) if safe_notes else "(no notes)"
    prompt = _IMPROVE_PROMPT.format(
        name=skill.name,
        description=skill.description,
        body=skill.body,
        failure_notes=notes_text,
    )
    new_body = await _call_llm(prompt)
    if not new_body or len(new_body.strip()) < 20:
        logger.warning("auto_evolver: LLM returned empty/short result for %s", skill.id)
        return None

    fingerprint = hashlib.sha256(
        f"{skill.name}\n{skill.description}\n{new_body}".encode()
    ).hexdigest()

    # Dedup — skip if fingerprint already exists as an accepted SkillRecord
    existing = await db.execute(
        select(SkillRecord).where(SkillRecord.content_fingerprint == fingerprint)
    )
    if existing.scalar_one_or_none():
        logger.info("auto_evolver: fingerprint already exists for %s, skipping", skill.id)
        return None

    new_version = _bump_patch(skill.version)
    candidate_id = f"{skill.slug}_auto_{new_version.replace('.', '_')}"

    safe_summary_notes = _sanitize_notes(failure_notes[:3])
    change_summary = (
        f"Auto-evolved from {skill.id} based on execution quality metrics. "
        f"Failure notes: {'; '.join(safe_summary_notes)}"
    )

    evo = SkillEvolution(
        id=str(uuid.uuid4()),
        parent_skill_id=skill.slug,
        candidate_skill_id=candidate_id,
        origin="fixed",
        status="pending",
        proposed_name=skill.name,
        proposed_desc=skill.description,
        proposed_body=new_body,
        change_summary=change_summary,
        proposed_by=triggered_by,
        tags=skill.tags,
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
