"""Ingest API — accepts OpenSpace ExecutionAnalysis and drives skill self-evolution.

Flow per ingested analysis:
  1. For each SkillJudgment, find the matching SkillRecord and update quality counters.
  2. After counter update, check thresholds via auto_evolver.should_evolve().
  3. If thresholds crossed, call auto_evolver.maybe_evolve() to generate and
     submit a new SkillEvolution (status=pending, goes through normal evaluator).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.models.db import ExecutionRun, SkillRecord
from app.schemas.api import IngestionResult, OpenSpaceIngestionRequest
from app.services import auto_evolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/openspace",
    status_code=status.HTTP_200_OK,
    response_model=IngestionResult,
)
async def ingest_openspace(
    body: OpenSpaceIngestionRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> IngestionResult:
    """Accept one ExecutionAnalysis from OpenSpace and update skill quality counters.

    Automatically triggers evolution proposals for skills that cross quality thresholds.
    """
    counters_updated: list[str] = []
    evolutions_triggered: list[str] = []

    # Collect failure notes keyed by skill_id for the evolver
    failure_notes_by_skill: dict[str, list[str]] = {}

    # --- Update quality counters for each SkillJudgment ---
    for judgment in body.skill_judgments:
        result = await db.execute(
            select(SkillRecord).where(SkillRecord.id == judgment.skill_id)
        )
        skill: Optional[SkillRecord] = result.scalar_one_or_none()
        if skill is None:
            logger.debug("ingest: skill %r not in registry, skipping", judgment.skill_id)
            continue

        skill.total_selections += 1

        if judgment.skill_applied:
            skill.total_applied += 1
            if body.task_completed:
                skill.total_completions += 1
        else:
            if not body.task_completed:
                skill.total_fallbacks += 1

        db.add(skill)
        counters_updated.append(skill.id)

        if judgment.note:
            failure_notes_by_skill.setdefault(skill.id, []).append(judgment.note)

    if body.execution_note:
        for sid in counters_updated:
            failure_notes_by_skill.setdefault(sid, []).append(body.execution_note)

    await db.flush()

    # --- Store the execution run for audit trail ---
    import uuid as _uuid
    from datetime import datetime, timezone
    run = ExecutionRun(
        id=str(_uuid.uuid4()),
        skill_id=body.skill_judgments[0].skill_id if body.skill_judgments else None,
        task=f"[openspace] {body.task_id}",
        status="done" if body.task_completed else "failed",
        executor_type="reasoning",
        target_env={"source": "openspace", "analyzed_by": body.analyzed_by},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        run_log=body.execution_note or None,
        called_by=owner,
    )
    db.add(run)
    await db.flush()

    # --- Check thresholds and trigger auto-evolution ---
    for skill_id in counters_updated:
        result = await db.execute(
            select(SkillRecord).where(SkillRecord.id == skill_id)
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            continue

        should, reason = auto_evolver.should_evolve(skill)
        if not should:
            continue

        logger.info("auto_evolver: skill %s crossed threshold (%s)", skill_id, reason)

        notes = failure_notes_by_skill.get(skill_id, [])
        notes.insert(0, f"Threshold crossed: {reason}")

        evo_id = await auto_evolver.maybe_evolve(
            skill=skill,
            failure_notes=notes,
            db=db,
            triggered_by=owner,
        )
        if evo_id:
            evolutions_triggered.append(skill_id)

    return IngestionResult(
        task_id=body.task_id,
        judgments_processed=len(body.skill_judgments),
        counters_updated=counters_updated,
        evolutions_triggered=evolutions_triggered,
    )
