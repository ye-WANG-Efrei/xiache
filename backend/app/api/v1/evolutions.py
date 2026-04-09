"""Evolutions API — PR-like workflow for proposing skill changes.

Lifecycle:
  propose (POST /evolutions)
    → evaluating (automatic checks run immediately)
    → accepted (auto, if score >= AUTO_ACCEPT_THRESHOLD)   → SkillRecord created
    → pending  (manual review needed, 0.3 <= score < threshold)
    → rejected (score < 0.3, or manually via POST /evolutions/{id}/reject)

Manual overrides:
  POST /evolutions/{id}/accept  — promote a pending evolution to accepted
  POST /evolutions/{id}/reject  — reject a pending evolution with a reason
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core import storage
from app.core.config import get_settings
from app.core.database import get_db
from app.models.db import Artifact, SkillEvolution, SkillLineage, SkillRecord
from app.schemas.api import (
    EvaluationResult,
    EvolutionResponse,
    ProposeEvolutionRequest,
)
from app.services import embedding as emb_service
from app.services.evaluator import evaluate_evolution
from app.services.skill_parser import parse_skill_md

router = APIRouter(prefix="/evolutions", tags=["evolutions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _evolution_to_response(
    evo: SkillEvolution,
    evaluation: Optional[EvaluationResult] = None,
) -> EvolutionResponse:
    return EvolutionResponse(
        evolution_id=evo.id,
        status=evo.status,
        proposed_name=evo.proposed_name,
        proposed_desc=evo.proposed_desc,
        parent_skill_id=evo.parent_skill_id,
        candidate_skill_id=evo.candidate_skill_id,
        origin=evo.origin,
        proposed_by=evo.proposed_by,
        proposed_at=evo.proposed_at,
        evaluated_at=evo.evaluated_at,
        evaluation=evaluation,
        result_record_id=evo.result_record_id,
        change_summary=evo.change_summary,
        tags=evo.tags,
        auto_accepted=evo.auto_accepted,
    )


def _rebuild_evaluation_from_evo(evo: SkillEvolution) -> Optional[EvaluationResult]:
    """Reconstruct the EvaluationResult from stored fields if the evolution
    has already been evaluated. Returns None if not yet evaluated."""
    if evo.quality_score is None:
        return None
    # We don't store individual check results in the DB; synthesise a minimal
    # EvaluationResult from the stored score and notes so callers always get
    # a consistent shape.
    passed = evo.status == "accepted"
    return EvaluationResult(
        passed=passed,
        quality_score=evo.quality_score,
        notes=evo.evaluation_notes or "No notes recorded.",
        checks={},
    )


async def _create_skill_record_from_evolution(
    evo: SkillEvolution,
    artifact: Artifact,
    zip_bytes: bytes,
    owner: str,
    db: AsyncSession,
) -> SkillRecord:
    """Create a SkillRecord from an evolution's artifact.

    This mirrors the creation logic in records.py so both auto-accept and
    manual accept paths share the same implementation.
    """
    skill_meta = parse_skill_md(zip_bytes)

    merged_tags = list(dict.fromkeys(skill_meta["tags"] + (evo.tags or [])))

    emb_text = emb_service.build_embedding_text(
        skill_meta["name"] or evo.id,
        skill_meta["description"],
        merged_tags,
    )
    embedding = await emb_service.generate_embedding(emb_text)

    # Use candidate_skill_id if provided, otherwise fall back to evo:<uuid>
    record_id = evo.candidate_skill_id or f"evo:{evo.id}"

    # Guard: must not overwrite an existing SkillRecord
    collision = await db.execute(
        select(SkillRecord).where(SkillRecord.id == record_id)
    )
    if collision.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"candidate_skill_id {record_id!r} already exists as a skill record.",
        )

    record = SkillRecord(
        id=record_id,
        artifact_id=evo.artifact_id,
        name=skill_meta["name"] or evo.id,
        description=skill_meta["description"],
        version=skill_meta.get("version", "1.0.0"),
        origin=evo.origin,
        visibility="public",
        level="tool_guide",
        tags=merged_tags,
        input_schema=skill_meta.get("input_schema", {}),
        output_schema=skill_meta.get("output_schema", {}),
        created_by=evo.proposed_by or owner,
        change_summary=evo.change_summary,
        content_diff=evo.content_diff,
        content_fingerprint=artifact.content_fingerprint,
        embedding=embedding,
        created_at=_utcnow(),
    )
    db.add(record)
    await db.flush()

    # Lineage edge if there is a parent
    if evo.parent_skill_id:
        lineage = SkillLineage(child_id=record_id, parent_id=evo.parent_skill_id)
        db.add(lineage)
        await db.flush()

    return record


# ---------------------------------------------------------------------------
# POST /evolutions — propose an evolution
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EvolutionResponse,
)
async def propose_evolution(
    body: ProposeEvolutionRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> EvolutionResponse:
    settings = get_settings()

    # Load artifact
    artifact_result = await db.execute(
        select(Artifact).where(Artifact.id == body.artifact_id)
    )
    artifact: Optional[Artifact] = artifact_result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {body.artifact_id!r} not found. Stage it first.",
        )

    # Load zip and parse SKILL.md
    try:
        zip_bytes = await storage.load_artifact(body.artifact_id)
        artifact_accessible = True
    except Exception:
        zip_bytes = b""
        artifact_accessible = False

    skill_meta = parse_skill_md(zip_bytes) if artifact_accessible else {
        "name": "", "description": "", "version": "0.0.0",
        "tags": [], "input_schema": {}, "output_schema": {}, "body": "",
    }

    proposed_name = skill_meta["name"]
    proposed_desc = skill_meta["description"]
    skill_body    = skill_meta["body"]

    # Pre-check 1: parent exists in DB (required when origin is derived/fixed)
    if body.parent_skill_id:
        parent_result = await db.execute(
            select(SkillRecord).where(SkillRecord.id == body.parent_skill_id)
        )
        parent_exists = parent_result.scalar_one_or_none() is not None
    else:
        parent_exists = True  # captured origin — no parent needed

    # Pre-check 2: duplicate detection via content fingerprint
    dup_result = await db.execute(
        select(SkillRecord).where(
            SkillRecord.content_fingerprint == artifact.content_fingerprint
        )
    )
    is_duplicate = dup_result.scalar_one_or_none() is not None

    # Run evaluation
    eval_result: EvaluationResult = evaluate_evolution(
        skill_name=proposed_name,
        skill_description=proposed_desc,
        skill_body=skill_body,
        skill_version=skill_meta.get("version", ""),
        skill_tags=skill_meta.get("tags", []),
        origin=body.origin,
        parent_skill_id=body.parent_skill_id,
        change_summary=body.change_summary,
        parent_exists=parent_exists,
        artifact_accessible=artifact_accessible,
        is_duplicate=is_duplicate,
    )

    now = _utcnow()
    evo_id = str(uuid.uuid4())

    # Determine status after evaluation
    if eval_result.passed and eval_result.quality_score >= settings.AUTO_ACCEPT_THRESHOLD:
        evo_status = "accepted"
    elif eval_result.quality_score < 0.3:
        evo_status = "rejected"
    else:
        evo_status = "pending"

    evo = SkillEvolution(
        id=evo_id,
        artifact_id=body.artifact_id,
        parent_skill_id=body.parent_skill_id,
        candidate_skill_id=body.candidate_skill_id,
        origin=body.origin,
        status="evaluating",          # transient — updated below
        proposed_name=proposed_name,
        proposed_desc=proposed_desc,
        change_summary=body.change_summary,
        content_diff=body.content_diff,
        proposed_by=owner,
        tags=body.tags,
        proposed_at=now,
        evaluated_at=now,
        evaluation_notes=eval_result.notes,
        quality_score=eval_result.quality_score,
        auto_accepted=False,
    )

    result_record_id: Optional[str] = None

    if evo_status == "accepted":
        # Auto-accept: create SkillRecord
        record = await _create_skill_record_from_evolution(
            evo=evo,
            artifact=artifact,
            zip_bytes=zip_bytes,
            owner=owner,
            db=db,
        )
        evo.status = "accepted"
        evo.result_record_id = record.id
        evo.auto_accepted = True
        result_record_id = record.id
    else:
        evo.status = evo_status

    db.add(evo)
    await db.flush()

    return _evolution_to_response(evo, evaluation=eval_result)


# ---------------------------------------------------------------------------
# GET /evolutions/{evolution_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{evolution_id}",
    response_model=EvolutionResponse,
)
async def get_evolution(
    evolution_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> EvolutionResponse:
    result = await db.execute(
        select(SkillEvolution).where(SkillEvolution.id == evolution_id)
    )
    evo: Optional[SkillEvolution] = result.scalar_one_or_none()
    if evo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evolution {evolution_id!r} not found.",
        )
    return _evolution_to_response(evo, evaluation=_rebuild_evaluation_from_evo(evo))


# ---------------------------------------------------------------------------
# GET /evolutions — list evolutions
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=dict,
)
async def list_evolutions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    parent_skill_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = select(SkillEvolution).order_by(SkillEvolution.proposed_at.desc())
    count_q = select(func.count()).select_from(SkillEvolution)

    if status_filter:
        q = q.where(SkillEvolution.status == status_filter)
        count_q = count_q.where(SkillEvolution.status == status_filter)
    if parent_skill_id:
        q = q.where(SkillEvolution.parent_skill_id == parent_skill_id)
        count_q = count_q.where(SkillEvolution.parent_skill_id == parent_skill_id)

    total: int = (await db.execute(count_q)).scalar_one()

    q = q.offset(offset).limit(limit)
    rows = list((await db.execute(q)).scalars().all())

    items = [
        _evolution_to_response(evo, evaluation=_rebuild_evaluation_from_evo(evo))
        for evo in rows
    ]

    return {"items": [item.model_dump() for item in items], "total": total}


# ---------------------------------------------------------------------------
# POST /evolutions/{evolution_id}/accept — manually accept a pending evolution
# ---------------------------------------------------------------------------


@router.post(
    "/{evolution_id}/accept",
    response_model=EvolutionResponse,
)
async def accept_evolution(
    evolution_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> EvolutionResponse:
    result = await db.execute(
        select(SkillEvolution).where(SkillEvolution.id == evolution_id)
    )
    evo: Optional[SkillEvolution] = result.scalar_one_or_none()
    if evo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evolution {evolution_id!r} not found.",
        )
    if evo.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Evolution {evolution_id!r} has status {evo.status!r}; "
                "only 'pending' evolutions can be manually accepted."
            ),
        )

    # Load artifact
    artifact_result = await db.execute(
        select(Artifact).where(Artifact.id == evo.artifact_id)
    )
    artifact: Optional[Artifact] = artifact_result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {evo.artifact_id!r} for evolution {evolution_id!r} not found.",
        )

    zip_bytes = await storage.load_artifact(evo.artifact_id)

    record = await _create_skill_record_from_evolution(
        evo=evo,
        artifact=artifact,
        zip_bytes=zip_bytes,
        owner=owner,
        db=db,
    )

    evo.status = "accepted"
    evo.result_record_id = record.id
    evo.evaluated_at = _utcnow()
    evo.auto_accepted = False

    db.add(evo)
    await db.flush()

    return _evolution_to_response(evo, evaluation=_rebuild_evaluation_from_evo(evo))


# ---------------------------------------------------------------------------
# POST /evolutions/{evolution_id}/reject — reject a pending evolution
# ---------------------------------------------------------------------------


@router.post(
    "/{evolution_id}/reject",
    response_model=EvolutionResponse,
)
async def reject_evolution(
    evolution_id: str,
    reason: str = Body(..., embed=True),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> EvolutionResponse:
    result = await db.execute(
        select(SkillEvolution).where(SkillEvolution.id == evolution_id)
    )
    evo: Optional[SkillEvolution] = result.scalar_one_or_none()
    if evo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evolution {evolution_id!r} not found.",
        )
    if evo.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Evolution {evolution_id!r} has status {evo.status!r}; "
                "only 'pending' evolutions can be manually rejected."
            ),
        )

    existing_notes = evo.evaluation_notes or ""
    evo.evaluation_notes = (existing_notes + "\n" + reason).strip() if existing_notes else reason
    evo.status = "rejected"
    evo.evaluated_at = _utcnow()

    db.add(evo)
    await db.flush()

    return _evolution_to_response(evo, evaluation=_rebuild_evaluation_from_evo(evo))
