# Version 042426 — Categories + ZhipuAI Embedding Integration

Date: 2026-04-24

## Summary

Added semantic category system and wired up ZhipuAI `embedding-3` for real vector generation.  
Skills now have category prototypes (centroid embeddings) that accumulate as more skills are registered.  
Vector dimension upgraded from 1536 → 2048 to match ZhipuAI's output.

---

## Changes

### New file: `backend/app/api/v1/categories.py`

`GET /api/v1/categories` — returns all category prototypes ordered by `skill_count` desc.

```python
router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=CategoryListResponse)
async def list_categories(...) -> CategoryListResponse
```

Registered in `router.py`:
```python
from app.api.v1 import categories, evolutions, ingest, runs, search, skills
router.include_router(categories.router)
```

---

### New file: `backend/app/services/category.py`

Two functions:

| Function | Purpose |
|---|---|
| `upsert_prototype(category, embedding, db)` | Insert or incrementally update the centroid for a category. Uses running average: `new_centroid = (old * n + new) / (n+1)` |
| `detect_category(query_embedding, db)` | Return nearest category to a query vector (pgvector `<=>` cosine distance) |

Called from `POST /skills` whenever both `category` and `embedding` are present.

---

### New file: `backend/migrations/add_categories.sql`

Creates `category_prototypes` table:

```sql
CREATE TABLE IF NOT EXISTS category_prototypes (
    id          VARCHAR(255) PRIMARY KEY,
    label       VARCHAR(255) NOT NULL DEFAULT '',
    skill_count INTEGER      NOT NULL DEFAULT 0,
    embedding   vector(2048),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

Also adds `category VARCHAR(255)` column to `skill_records` and creates an index on it.

Applied manually:
```bash
docker exec -i xiache-postgres psql -U xiache -d xiache < backend/migrations/add_categories.sql
```

---

### `backend/app/api/v1/skills.py`

`create_skill` now calls `cat_service.upsert_prototype` after a successful embedding:

```python
if body.category and embedding:
    await cat_service.upsert_prototype(body.category, embedding, db)
```

---

### `backend/app/services/embedding.py`

ZhipuAI's `/embeddings` endpoint does not accept a `dimensions` parameter (unlike OpenAI).  
Added a provider check to omit `dimensions` when `EMBEDDING_API_BASE` points to `bigmodel.cn`:

```python
kwargs: dict = {"input": text, "model": settings.EMBEDDING_MODEL}
if settings.EMBEDDING_API_BASE and "bigmodel" not in settings.EMBEDDING_API_BASE:
    kwargs["dimensions"] = settings.EMBEDDING_DIMENSIONS
response = await client.embeddings.create(**kwargs)
```

No new dependency — continues to use the existing `openai` SDK pointed at ZhipuAI's OpenAI-compatible endpoint.

---

### `backend/app/models/db.py`

```python
# before
embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

# after (both SkillRecord and CategoryPrototype)
embedding: Mapped[Optional[Any]] = mapped_column(Vector(2048), nullable=True)
```

---

### Database: vector column migration

```sql
-- Run once on existing DB
DROP INDEX IF EXISTS idx_skill_records_embedding;
DROP INDEX IF EXISTS idx_category_prototypes_embedding;
ALTER TABLE skill_records ALTER COLUMN embedding TYPE vector(2048);
ALTER TABLE category_prototypes ALTER COLUMN embedding TYPE vector(2048);
```

> **No vector indexes recreated.** pgvector's ivfflat and hnsw both cap at 2000 dimensions; 2048 exceeds that limit. For MVP scale (< 10k skills), sequential scan is exact and fast enough. Indexes can be added later if needed via a dedicated ANN approach.

---

### `.env` / `.env.example`

```env
# before
EMBEDDING_API_KEY=
EMBEDDING_API_BASE=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# after
EMBEDDING_API_KEY=<zhipuai-key>
EMBEDDING_API_BASE=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=2048
```

---

### `backend/app/schemas/api.py`

Added `CategoryItem` and `CategoryListResponse` schemas (inferred from usage — not shown here).

---

### `backend/app/api/v1/search.py` — asyncpg vector cast fix

SQLAlchemy `text()` with asyncpg cannot combine a named parameter and a PostgreSQL type cast in the form `:param::type`. Changed module-level `text()` constants to functions that embed the vector literal directly via f-string:

```python
# before (breaks asyncpg)
_SQL_HYBRID_SCOPED = text("... embedding <=> :embedding::vector ...")

# after
def _sql_hybrid_scoped(vec_literal: str) -> text:
    return text(f"... embedding <=> '{vec_literal}'::vector ...")
```

`embedding` removed from the named-parameter dict; `vec_literal` is a float-only string so there is no injection risk.

---

### `backend/app/services/category.py` — asyncpg vector cast fix

Same issue in `detect_category`. Changed from:

```python
text("... ORDER BY embedding <=> :qvec::vector ..."), {"qvec": vec_literal}
```

to:

```python
text(f"... ORDER BY embedding <=> '{vec_literal}'::vector ...")
```

---

### `smoke-test.md`

- T2: added `"category": "demo"` to registration payload; updated expected response; noted `embedding` field is always `null` in response (use `?include_embedding=true` to verify)
- T4: added `?include_embedding=true` snippet to verify 2048-dim vector
- **New T7**: `GET /categories` — verifies category prototype was created with correct `skill_count`
- Old T7–T10 renumbered to T8–T11
- Quick script: removed stale `assert d['slug']` assertion; added T7 categories assertion
- Summary table updated

---

## What did NOT change

- `/api/v1/skills` route prefix and all existing endpoints
- Deduplication / fingerprinting logic
- Evolution flow and evaluator checks
- Frontend components
- Auth mechanism (`Bearer` token, dev mode)
