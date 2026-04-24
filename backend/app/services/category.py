"""Category prototype management.

Each category is represented by a centroid embedding — the running average of
all skill embeddings registered under that category.  We update it incrementally
so we never need to re-scan the entire table:

    new_centroid = (old_centroid * old_count + new_embedding) / new_count
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import CategoryPrototype

logger = logging.getLogger(__name__)


async def upsert_prototype(
    category: str,
    embedding: list[float],
    db: AsyncSession,
) -> None:
    """Insert or incrementally update the centroid for *category*."""
    proto = (
        await db.execute(select(CategoryPrototype).where(CategoryPrototype.id == category))
    ).scalar_one_or_none()

    if proto is None:
        db.add(CategoryPrototype(
            id=category,
            label=category,
            skill_count=1,
            embedding=embedding,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))
        logger.info("category created: %s", category)
        return

    n = proto.skill_count
    if proto.embedding is None:
        new_emb = embedding
    else:
        old = list(proto.embedding)
        new_emb = [(old[i] * n + embedding[i]) / (n + 1) for i in range(len(old))]

    proto.embedding = new_emb
    proto.skill_count = n + 1
    proto.updated_at = datetime.now(timezone.utc)
    logger.info("category updated: %s (count=%d)", category, proto.skill_count)


async def detect_category(
    query_embedding: list[float],
    db: AsyncSession,
) -> str | None:
    """Return the category whose prototype is nearest to *query_embedding*.

    Returns None when no prototypes exist yet (empty registry).
    """
    vec_literal = "[" + ",".join(f"{v:.8f}" for v in query_embedding) + "]"
    row = (await db.execute(
        text(f"""
            SELECT id FROM category_prototypes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> '{vec_literal}'::vector
            LIMIT 1
        """),
    )).fetchone()
    return row[0] if row else None
