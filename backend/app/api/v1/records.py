from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.models.db import SkillLineage, SkillRecord
from app.schemas.api import (
    CreateRecordRequest,
    ErrorResponse,
    RecordMetadataItem,
    RecordMetadataResponse,
    RecordResponse,
)
from app.services import embedding as emb_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/records", tags=["records"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fingerprint(name: str, description: str, body: str) -> str:
    content = f"{name}\n{description}\n{body}"
    return hashlib.sha256(content.encode()).hexdigest()


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
        body=record.body,
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
    fingerprint = _fingerprint(body.name, body.description, body.body)

    # Dedup: same record_id
    existing_by_id = (await db.execute(
        select(SkillRecord).where(SkillRecord.id == body.record_id)
    )).scalar_one_or_none()

    # Dedup: same content fingerprint
    existing_by_fp = (await db.execute(
        select(SkillRecord).where(SkillRecord.content_fingerprint == fingerprint)
    )).scalar_one_or_none()

    if existing_by_id is not None:
        if existing_by_id.content_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse(
                    error="record_id_fingerprint_conflict",
                    detail=f"Record {body.record_id!r} already exists with different content.",
                    existing_record_id=existing_by_id.id,
                    fingerprint=existing_by_id.content_fingerprint,
                ).model_dump(),
            )
        parent_ids = await _get_parent_ids(db, existing_by_id.id)
        return _record_to_response(existing_by_id, parent_ids)

    if existing_by_fp is not None and existing_by_fp.id != body.record_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error="fingerprint_record_id_conflict",
                detail=f"Same content already registered under record {existing_by_fp.id!r}.",
                existing_record_id=existing_by_fp.id,
                fingerprint=fingerprint,
            ).model_dump(),
        )

    # Generate embedding
    emb_text = emb_service.build_embedding_text(body.name, body.description, body.tags)
    embedding = await emb_service.generate_embedding(emb_text)

    record = SkillRecord(
        id=body.record_id,
        artifact_id=None,
        name=body.name,
        description=body.description,
        body=body.body,
        version=body.version,
        origin=body.origin,
        visibility=body.visibility,
        level=body.level,
        tags=body.tags,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        created_by=body.created_by or owner,
        change_summary=body.change_summary or "",
        content_diff=body.content_diff,
        content_fingerprint=fingerprint,
        embedding=embedding,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()

    for parent_id in body.parent_skill_ids:
        db.add(SkillLineage(child_id=body.record_id, parent_id=parent_id))

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
    rows: list[SkillRecord] = list((await db.execute(q)).scalars().all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.id, last.created_at)

    record_ids = [r.id for r in rows]
    lineage_rows = (await db.execute(
        select(SkillLineage).where(SkillLineage.child_id.in_(record_ids))
    )).scalars().all()
    parents_map: dict[str, list[str]] = {rid: [] for rid in record_ids}
    for lin in lineage_rows:
        parents_map[lin.child_id].append(lin.parent_id)

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
                body=rec.body,
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

    return RecordMetadataResponse(items=items, has_more=has_more, next_cursor=next_cursor, total=total)


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
    record = (await db.execute(
        select(SkillRecord).where(SkillRecord.id == record_id)
    )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Record {record_id!r} not found")
    parent_ids = await _get_parent_ids(db, record_id)
    return _record_to_response(record, parent_ids, include_embedding=include_embedding)


# ---------------------------------------------------------------------------
# GET /records/{record_id}/download  — returns Markdown text
# ---------------------------------------------------------------------------


@router.get("/{record_id}/download")
async def download_record(
    record_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    record = (await db.execute(
        select(SkillRecord).where(SkillRecord.id == record_id)
    )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Record {record_id!r} not found")

    tag_lines = "\n".join(f"  - {t}" for t in (record.tags or []))
    tag_block = f"tags:\n{tag_lines}" if tag_lines else "tags: []"
    markdown = (
        f"---\n"
        f"name: {record.name}\n"
        f"description: {record.description}\n"
        f"version: {record.version}\n"
        f"{tag_block}\n"
        f"---\n\n"
        f"{record.body}"
    )
    return Response(
        content=markdown.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.md"'},
    )
