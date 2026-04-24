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
from app.services import category as cat_service
from app.services import embedding as emb_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# ---------------------------------------------------------------------------
# SQL templates
# ---------------------------------------------------------------------------

def _sql_hybrid_scoped(vec_literal: str) -> text:
    return text(f"""
WITH vec_candidates AS (
    SELECT
        id,
        1 - (embedding <=> '{vec_literal}'::vector) AS vec_score
    FROM skill_records
    WHERE embedding IS NOT NULL
      AND category = :category
    ORDER BY embedding <=> '{vec_literal}'::vector
    LIMIT :pool
),
fts_candidates AS (
    SELECT
        id,
        ts_rank(
            to_tsvector('english', name || ' ' || description || ' ' || body
                || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v))),
            plainto_tsquery('english', :query)
        ) AS fts_score
    FROM skill_records
    WHERE category = :category
      AND to_tsvector('english', name || ' ' || description || ' ' || body
          || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v)))
          @@ plainto_tsquery('english', :query)
)
SELECT
    r.id, r.name, r.description, r.origin, r.visibility, r.level,
    r.tags, r.created_by, r.created_at, r.category,
    COALESCE(v.vec_score, 0) * 0.6 + COALESCE(f.fts_score, 0) * 0.4 AS score
FROM skill_records r
LEFT JOIN vec_candidates v ON r.id = v.id
LEFT JOIN fts_candidates f ON r.id = f.id
WHERE v.id IS NOT NULL OR f.id IS NOT NULL
ORDER BY score DESC
LIMIT :limit
""")


def _sql_hybrid_global(vec_literal: str) -> text:
    return text(f"""
WITH vec_candidates AS (
    SELECT
        id,
        1 - (embedding <=> '{vec_literal}'::vector) AS vec_score
    FROM skill_records
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> '{vec_literal}'::vector
    LIMIT :pool
),
fts_candidates AS (
    SELECT
        id,
        ts_rank(
            to_tsvector('english', name || ' ' || description || ' ' || body
                || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v))),
            plainto_tsquery('english', :query)
        ) AS fts_score
    FROM skill_records
    WHERE to_tsvector('english', name || ' ' || description || ' ' || body
          || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v)))
          @@ plainto_tsquery('english', :query)
)
SELECT
    r.id, r.name, r.description, r.origin, r.visibility, r.level,
    r.tags, r.created_by, r.created_at, r.category,
    COALESCE(v.vec_score, 0) * 0.6 + COALESCE(f.fts_score, 0) * 0.4 AS score
FROM skill_records r
LEFT JOIN vec_candidates v ON r.id = v.id
LEFT JOIN fts_candidates f ON r.id = f.id
WHERE v.id IS NOT NULL OR f.id IS NOT NULL
ORDER BY score DESC
LIMIT :limit
""")

# FTS-only fallback (no embedding service configured).
_SQL_FTS = text("""
SELECT
    id, name, description, origin, visibility, level,
    tags, created_by, created_at, category,
    ts_rank(
        to_tsvector('english', name || ' ' || description || ' ' || body
            || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v))),
        plainto_tsquery('english', :query)
    ) AS score
FROM skill_records
WHERE to_tsvector('english', name || ' ' || description || ' ' || body
      || ' ' || (SELECT coalesce(string_agg(v,' '),'') FROM jsonb_array_elements_text(tags) t(v)))
      @@ plainto_tsquery('english', :query)
ORDER BY score DESC
LIMIT :limit
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vec_to_pg(embedding: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _row_to_result(row: dict) -> SearchResult:
    return SearchResult(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        origin=row["origin"],
        visibility=row["visibility"],
        level=row["level"],
        tags=row["tags"] if isinstance(row["tags"], list) else [],
        created_by=row["created_by"] or "",
        created_at=row["created_at"],
        score=float(row["score"]),
        category=row.get("category"),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=SearchResponse, summary="Search skills with semantic category routing")
async def search_skills(
    q: str = Query(..., min_length=1, max_length=500, description="Natural-language query"),
    limit: int = Query(default=20, ge=1, le=100),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Two-stage semantic search.

    Stage 1 — Category routing: embed the query and find the nearest category
    prototype via cosine similarity.  No string matching required from the caller.

    Stage 2 — Skill retrieval: hybrid vector + full-text search within the
    detected category.

    Falls back to global search when no category prototypes exist yet, or to
    full-text-only when no embedding service is configured.
    """
    query = q.strip()
    detected_category: Optional[str] = None
    search_type: str = "fulltext"

    # Try to generate query embedding
    query_embedding: Optional[list[float]] = None
    try:
        query_embedding = await emb_service.generate_embedding(query)
    except Exception as exc:
        logger.warning("embedding failed, falling back to FTS: %s", exc)

    if query_embedding:
        # Stage 1: semantic category routing
        detected_category = await cat_service.detect_category(query_embedding, db)
        logger.info("query=%r → detected_category=%r", query, detected_category)

        vec_pg = _vec_to_pg(query_embedding)

        if detected_category:
            result = await db.execute(
                _sql_hybrid_scoped(vec_pg),
                {"query": query, "category": detected_category, "pool": limit * 5, "limit": limit},
            )
            search_type = "hybrid_scoped"
        else:
            # No prototypes yet — global hybrid search
            result = await db.execute(
                _sql_hybrid_global(vec_pg),
                {"query": query, "pool": limit * 5, "limit": limit},
            )
            search_type = "hybrid"
    else:
        # No embedding service — plain FTS, no category routing possible
        result = await db.execute(_SQL_FTS, {"query": query, "limit": limit})

    rows = result.mappings().all()
    results = [_row_to_result(dict(row)) for row in rows]

    logger.info(
        "search q=%r type=%s category=%r results=%d",
        query, search_type, detected_category, len(results),
    )

    return SearchResponse(
        query=query,
        results=results,
        count=len(results),
        search_type=search_type,
        detected_category=detected_category,
    )
