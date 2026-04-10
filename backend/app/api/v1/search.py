from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.schemas.api import SearchResponse, SearchResult
from app.services import embedding as emb_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# ---------------------------------------------------------------------------
# SQL templates
# ---------------------------------------------------------------------------

# Hybrid: pgvector cosine similarity + PostgreSQL full-text search.
# Both scores are in [0, 1]; combined with configurable weights.
_SQL_HYBRID = text("""
WITH vec_candidates AS (
    SELECT
        id,
        1 - (embedding <=> :embedding::vector) AS vec_score
    FROM skill_records
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> :embedding::vector
    LIMIT :pool
),
fts_candidates AS (
    SELECT
        id,
        ts_rank(
            to_tsvector('english', name || ' ' || description || ' ' || body || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v))),
            plainto_tsquery('english', :query)
        ) AS fts_score
    FROM skill_records
    WHERE to_tsvector('english', name || ' ' || description || ' ' || body || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v)))
          @@ plainto_tsquery('english', :query)
)
SELECT
    r.id          AS record_id,
    r.name,
    r.description,
    r.origin,
    r.visibility,
    r.level,
    r.tags,
    r.created_by,
    r.created_at,
    COALESCE(v.vec_score, 0) * 0.6
        + COALESCE(f.fts_score, 0) * 0.4  AS score
FROM skill_records r
LEFT JOIN vec_candidates v ON r.id = v.id
LEFT JOIN fts_candidates f ON r.id = f.id
WHERE v.id IS NOT NULL OR f.id IS NOT NULL
ORDER BY score DESC
LIMIT :limit
""")

# Fallback: full-text search only (when embedding service is not configured).
_SQL_FTS = text("""
SELECT
    id          AS record_id,
    name,
    description,
    origin,
    visibility,
    level,
    tags,
    created_by,
    created_at,
    ts_rank(
        to_tsvector('english', name || ' ' || description || ' ' || body || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v))),
        plainto_tsquery('english', :query)
    ) AS score
FROM skill_records
WHERE to_tsvector('english', name || ' ' || description || ' ' || body || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v)))
      @@ plainto_tsquery('english', :query)
ORDER BY score DESC
LIMIT :limit
""")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _vec_to_pg(embedding: list[float]) -> str:
    """Convert a Python float list to PostgreSQL vector literal '[x,y,…]'."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _row_to_result(row: dict) -> SearchResult:
    return SearchResult(
        record_id=row["record_id"],
        name=row["name"],
        description=row["description"] or "",
        origin=row["origin"],
        visibility=row["visibility"],
        level=row["level"],
        tags=row["tags"] if isinstance(row["tags"], list) else [],
        created_by=row["created_by"] or "",
        created_at=row["created_at"],
        score=float(row["score"]),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=SearchResponse, summary="Search skills")
async def search_skills(
    q: str = Query(..., min_length=1, max_length=500, description="Natural-language search query"),
    limit: int = Query(default=20, ge=1, le=100),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Hybrid semantic + full-text search over all skills.

    - When an embedding service is configured: uses **pgvector cosine similarity**
      (0.6 weight) + **PostgreSQL FTS ts_rank** (0.4 weight).
    - When no embedding service: falls back to **full-text search only**.

    Results are sorted by combined score (highest first).
    """
    query = q.strip()

    # Try to generate query embedding
    query_embedding: Optional[list[float]] = None
    try:
        query_embedding = await emb_service.generate_embedding(query)
    except Exception as exc:
        logger.warning("Embedding generation failed, falling back to FTS: %s", exc)

    if query_embedding:
        result = await db.execute(
            _SQL_HYBRID,
            {
                "query": query,
                "embedding": _vec_to_pg(query_embedding),
                "pool": limit * 5,   # pull 5× more candidates for reranking
                "limit": limit,
            },
        )
        search_type = "hybrid"
    else:
        result = await db.execute(
            _SQL_FTS,
            {"query": query, "limit": limit},
        )
        search_type = "fulltext"

    rows = result.mappings().all()
    results = [_row_to_result(dict(row)) for row in rows]

    logger.info(
        "search q=%r type=%s results=%d", query, search_type, len(results)
    )

    return SearchResponse(
        query=query,
        results=results,
        count=len(results),
        search_type=search_type,
    )
