from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import require_auth
from app.core import storage
from app.core.database import get_db
from app.models.db import Artifact, SkillLineage, SkillRecord
from app.schemas.api import (
    CreateRecordRequest,
    ErrorResponse,
    RecordMetadataItem,
    RecordMetadataResponse,
    RecordResponse,
)
from app.services import embedding as emb_service
from app.services.skill_parser import parse_skill_md

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/records", tags=["records"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_cursor(record_id: str, created_at: datetime) -> str:
    payload = json.dumps({"id": record_id, "ts": created_at.isoformat()})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, datetime]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return payload["id"], datetime.fromisoformat(payload["ts"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor: {exc}",
        ) from exc


async def _get_parent_ids(db: AsyncSession, record_id: str) -> list[str]:
    result = await db.execute(
        select(SkillLineage.parent_id).where(SkillLineage.child_id == record_id)
    )
    return [row[0] for row in result.fetchall()]


def _record_to_response(
    record: SkillRecord,
    parent_ids: list[str],
    include_embedding: bool = False,
) -> RecordResponse:
    embedding_out = None
    if include_embedding and record.embedding is not None:
        embedding_out = list(record.embedding)

    return RecordResponse(
        record_id=record.id,
        artifact_id=record.artifact_id,
        artifact_ref=f"artifact://{record.id}",
        name=record.name,
        description=record.description,
        version=record.version,
        origin=record.origin,
        visibility=record.visibility,
        level=record.level,
        tags=record.tags,
        input_schema=record.input_schema,
        output_schema=record.output_schema,
        created_by=record.created_by,
        change_summary=record.change_summary,
        content_diff=record.content_diff,
        content_fingerprint=record.content_fingerprint,
        parent_skill_ids=parent_ids,
        created_at=record.created_at,
        embedding=embedding_out,
    )


# ---------------------------------------------------------------------------
# POST /records
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": RecordResponse},
        409: {"model": ErrorResponse},
    },
)
async def create_record(
    body: CreateRecordRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    # Check that the artifact exists
    artifact_result = await db.execute(
        select(Artifact).where(Artifact.id == body.artifact_id)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {body.artifact_id!r} not found. Stage it first.",
        )

    # Dedup checks
    existing_by_id_result = await db.execute(
        select(SkillRecord).where(SkillRecord.id == body.record_id)
    )
    existing_by_id: Optional[SkillRecord] = existing_by_id_result.scalar_one_or_none()

    existing_by_fp_result = await db.execute(
        select(SkillRecord).where(
            SkillRecord.content_fingerprint == artifact.content_fingerprint
        )
    )
    existing_by_fp: Optional[SkillRecord] = existing_by_fp_result.scalar_one_or_none()

    if existing_by_id is not None:
        if existing_by_id.content_fingerprint != artifact.content_fingerprint:
            # Same record_id, different content
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse(
                    error="record_id_fingerprint_conflict",
                    detail=(
                        f"Record {body.record_id!r} already exists with a "
                        "different content fingerprint."
                    ),
                    existing_record_id=existing_by_id.id,
                    fingerprint=existing_by_id.content_fingerprint,
                ).model_dump(),
            )
        # Exact duplicate — idempotent OK, return the existing record
        parent_ids = await _get_parent_ids(db, existing_by_id.id)
        return _record_to_response(existing_by_id, parent_ids)

    if existing_by_fp is not None and existing_by_fp.id != body.record_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error="fingerprint_record_id_conflict",
                detail=(
                    f"Content fingerprint already registered under record "
                    f"{existing_by_fp.id!r}."
                ),
                existing_record_id=existing_by_fp.id,
                fingerprint=artifact.content_fingerprint,
            ).model_dump(),
        )

    # Parse SKILL.md from zip
    zip_bytes = await storage.load_artifact(body.artifact_id)
    skill_meta = parse_skill_md(zip_bytes)

    # Merge tags: SKILL.md tags + request tags, deduplicated
    merged_tags = list(dict.fromkeys(skill_meta["tags"] + body.tags))

    # Schemas: request overrides SKILL.md if non-empty
    input_schema = body.input_schema or skill_meta["input_schema"]
    output_schema = body.output_schema or skill_meta["output_schema"]

    # Version: request overrides SKILL.md if not default
    version = body.version if body.version != "1.0.0" else (skill_meta["version"] or "1.0.0")

    # Generate embedding
    emb_text = emb_service.build_embedding_text(
        skill_meta["name"] or body.record_id,
        skill_meta["description"],
        merged_tags,
    )
    embedding = await emb_service.generate_embedding(emb_text)

    # Create record
    record = SkillRecord(
        id=body.record_id,
        artifact_id=body.artifact_id,
        name=skill_meta["name"] or body.record_id,
        description=skill_meta["description"],
        version=version,
        origin=body.origin,
        visibility=body.visibility,
        level=body.level,
        tags=merged_tags,
        input_schema=input_schema,
        output_schema=output_schema,
        created_by=body.created_by or owner,
        change_summary=body.change_summary or "",
        content_diff=body.content_diff,
        content_fingerprint=artifact.content_fingerprint,
        embedding=embedding,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()

    # Lineage edges
    for parent_id in body.parent_skill_ids:
        lineage = SkillLineage(child_id=body.record_id, parent_id=parent_id)
        db.add(lineage)

    await db.flush()

    return _record_to_response(record, list(body.parent_skill_ids))


# ---------------------------------------------------------------------------
# GET /records/metadata
# ---------------------------------------------------------------------------


@router.get("/metadata", response_model=RecordMetadataResponse)
async def list_records_metadata(
    limit: int = Query(default=50, ge=1, le=500),
    cursor: Optional[str] = Query(default=None),
    include_embedding: bool = Query(default=False),
    visibility: Optional[str] = Query(default=None),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordMetadataResponse:
    """Return paginated skill record metadata, optionally with embeddings."""
    q = select(SkillRecord).order_by(SkillRecord.created_at.desc(), SkillRecord.id.desc())

    if visibility:
        q = q.where(SkillRecord.visibility == visibility)

    if cursor:
        _cursor_id, cursor_ts = _decode_cursor(cursor)
        q = q.where(
            (SkillRecord.created_at < cursor_ts)
            | (
                (SkillRecord.created_at == cursor_ts)
                & (SkillRecord.id < _cursor_id)
            )
        )

    q = q.limit(limit + 1)

    result = await db.execute(q)
    rows: list[SkillRecord] = list(result.scalars().all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.id, last.created_at)

    # Bulk-fetch parent IDs for all returned records
    record_ids = [r.id for r in rows]
    lineage_result = await db.execute(
        select(SkillLineage).where(SkillLineage.child_id.in_(record_ids))
    )
    lineage_rows = lineage_result.scalars().all()
    parents_map: dict[str, list[str]] = {rid: [] for rid in record_ids}
    for lin in lineage_rows:
        parents_map[lin.child_id].append(lin.parent_id)

    # Total count
    count_q = select(func.count()).select_from(SkillRecord)
    if visibility:
        count_q = count_q.where(SkillRecord.visibility == visibility)
    total: int = (await db.execute(count_q)).scalar_one()

    items = []
    for rec in rows:
        emb_out = None
        if include_embedding and rec.embedding is not None:
            emb_out = list(rec.embedding)
        items.append(
            RecordMetadataItem(
                record_id=rec.id,
                artifact_id=rec.artifact_id,
                artifact_ref=f"artifact://{rec.id}",
                name=rec.name,
                description=rec.description,
                version=rec.version,
                origin=rec.origin,
                visibility=rec.visibility,
                level=rec.level,
                tags=rec.tags,
                input_schema=rec.input_schema,
                output_schema=rec.output_schema,
                created_by=rec.created_by,
                change_summary=rec.change_summary,
                content_fingerprint=rec.content_fingerprint,
                parent_skill_ids=parents_map.get(rec.id, []),
                created_at=rec.created_at,
                embedding=emb_out,
            )
        )

    return RecordMetadataResponse(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /records/{record_id}
# ---------------------------------------------------------------------------


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: str,
    include_embedding: bool = Query(default=False),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    result = await db.execute(
        select(SkillRecord).where(SkillRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id!r} not found",
        )
    parent_ids = await _get_parent_ids(db, record_id)
    return _record_to_response(record, parent_ids, include_embedding=include_embedding)


# ---------------------------------------------------------------------------
# GET /records/{record_id}/download
# ---------------------------------------------------------------------------


@router.get("/{record_id}/download")
async def download_record(
    record_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(SkillRecord).where(SkillRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id!r} not found",
        )

    try:
        zip_bytes = await storage.load_artifact(record.artifact_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact file for record {record_id!r} is missing from storage",
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{record_id}.zip"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
