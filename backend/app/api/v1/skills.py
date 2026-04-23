from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import uuid
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

router = APIRouter(prefix="/skills", tags=["skills"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fingerprint(name: str, description: str, body: str) -> str:
    content = f"{name}\n{description}\n{body}"
    return hashlib.sha256(content.encode()).hexdigest()


def _encode_cursor(slug: str, created_at: datetime) -> str:
    payload = json.dumps({"slug": slug, "ts": created_at.isoformat()})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, datetime]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return payload["slug"], datetime.fromisoformat(payload["ts"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor: {exc}",
        ) from exc


async def _get_parent_slugs(db: AsyncSession, slug: str) -> list[str]:
    result = await db.execute(
        select(SkillLineage.parent_slug).where(SkillLineage.child_slug == slug)
    )
    return [row[0] for row in result.fetchall()]


def _record_to_response(
    record: SkillRecord,
    parent_slugs: list[str],
    include_embedding: bool = False,
) -> RecordResponse:
    embedding_out = None
    if include_embedding and record.embedding is not None:
        embedding_out = list(record.embedding)

    return RecordResponse(
        id=record.id,
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
        parent_skill_ids=parent_slugs,
        created_at=record.created_at,
        embedding=embedding_out,
    )


# ---------------------------------------------------------------------------
# POST /skills
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": RecordResponse},
        409: {"model": ErrorResponse},
    },
)
async def create_skill(
    body: CreateRecordRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    slug = body.record_id or re.sub(r"[^a-z0-9_-]", "_", body.name.lower().strip())
    fingerprint = _fingerprint(body.name, body.description, body.body)

    # Dedup: same slug
    existing_by_slug = (await db.execute(
        select(SkillRecord).where(SkillRecord.slug == slug)
    )).scalar_one_or_none()

    # Dedup: same content fingerprint
    existing_by_fp = (await db.execute(
        select(SkillRecord).where(SkillRecord.content_fingerprint == fingerprint)
    )).scalar_one_or_none()

    if existing_by_slug is not None:
        if existing_by_slug.content_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse(
                    error="record_id_fingerprint_conflict",
                    detail=f"Record {slug!r} already exists with different content.",
                    existing_record_id=existing_by_slug.slug,
                    fingerprint=existing_by_slug.content_fingerprint,
                ).model_dump(),
            )
        parent_slugs = await _get_parent_slugs(db, existing_by_slug.slug)
        return _record_to_response(existing_by_slug, parent_slugs)

    if existing_by_fp is not None and existing_by_fp.slug != slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error="fingerprint_record_id_conflict",
                detail=f"Same content already registered under record {existing_by_fp.slug!r}.",
                existing_record_id=existing_by_fp.slug,
                fingerprint=fingerprint,
            ).model_dump(),
        )

    # Generate embedding
    emb_text = emb_service.build_embedding_text(body.name, body.description, body.tags)
    embedding = await emb_service.generate_embedding(emb_text)

    record = SkillRecord(
        id=str(uuid.uuid4()),
        slug=slug,
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

    for parent_slug in body.parent_skill_ids:
        db.add(SkillLineage(child_slug=slug, parent_slug=parent_slug))

    await db.flush()
    return _record_to_response(record, list(body.parent_skill_ids))


# ---------------------------------------------------------------------------
# GET /skills/metadata
# ---------------------------------------------------------------------------


@router.get("/metadata", response_model=RecordMetadataResponse)
async def list_skills_metadata(
    limit: int = Query(default=50, ge=1, le=500),
    cursor: Optional[str] = Query(default=None),
    include_embedding: bool = Query(default=False),
    visibility: Optional[str] = Query(default=None),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordMetadataResponse:
    q = select(SkillRecord).order_by(SkillRecord.created_at.desc(), SkillRecord.slug.desc())

    if visibility:
        q = q.where(SkillRecord.visibility == visibility)

    if cursor:
        _cursor_slug, cursor_ts = _decode_cursor(cursor)
        q = q.where(
            (SkillRecord.created_at < cursor_ts)
            | (
                (SkillRecord.created_at == cursor_ts)
                & (SkillRecord.slug < _cursor_slug)
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
        next_cursor = _encode_cursor(last.slug, last.created_at)

    slugs = [r.slug for r in rows]
    lineage_rows = (await db.execute(
        select(SkillLineage).where(SkillLineage.child_slug.in_(slugs))
    )).scalars().all()
    parents_map: dict[str, list[str]] = {s: [] for s in slugs}
    for lin in lineage_rows:
        parents_map[lin.child_slug].append(lin.parent_slug)

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
                id=rec.id,
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
                parent_skill_ids=parents_map.get(rec.slug, []),
                created_at=rec.created_at,
                embedding=emb_out,
            )
        )

    return RecordMetadataResponse(items=items, has_more=has_more, next_cursor=next_cursor, total=total)


# ---------------------------------------------------------------------------
# GET /skills/{skill_id}
# ---------------------------------------------------------------------------


@router.get("/{skill_id}", response_model=RecordResponse)
async def get_skill(
    skill_id: str,
    include_embedding: bool = Query(default=False),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    record = (await db.execute(
        select(SkillRecord).where(SkillRecord.slug == skill_id)
    )).scalar_one_or_none()
    if record is None:
        # fallback: try UUID lookup
        record = (await db.execute(
            select(SkillRecord).where(SkillRecord.id == skill_id)
        )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {skill_id!r} not found")
    parent_slugs = await _get_parent_slugs(db, record.slug)
    return _record_to_response(record, parent_slugs, include_embedding=include_embedding)


# ---------------------------------------------------------------------------
# GET /skills/{skill_id}/download  — returns Markdown text
# ---------------------------------------------------------------------------


@router.get("/{skill_id}/download")
async def download_skill(
    skill_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    record = (await db.execute(
        select(SkillRecord).where(SkillRecord.slug == skill_id)
    )).scalar_one_or_none()
    if record is None:
        record = (await db.execute(
            select(SkillRecord).where(SkillRecord.id == skill_id)
        )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {skill_id!r} not found")

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
        headers={"Content-Disposition": f'attachment; filename="{skill_id}.md"'},
    )
