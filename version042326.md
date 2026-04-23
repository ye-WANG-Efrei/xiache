# Version 042326 — Route rename: /records → /skills

Date: 2026-04-23

## Summary

Renamed the REST resource from `/records` to `/skills` across the entire codebase.  
The data model and logic are unchanged; only the HTTP path prefix changed.

---

## Changes

### New file: `backend/app/api/v1/skills.py`

Created to replace `records.py` as the canonical router module.

- `router = APIRouter(prefix="/records", tags=["records"])`  
  → `router = APIRouter(prefix="/skills", tags=["skills"])`
- Handler names updated:  
  `create_record` → `create_skill`  
  `list_records_metadata` → `list_skills_metadata`  
  `get_record` → `get_skill`  
  `download_record` → `download_skill`
- Error messages: `"Record {id!r} not found"` → `"Skill {id!r} not found"`

`records.py` is now a dead file (no longer imported). Not deleted to avoid destructive ops.

---

### `backend/app/api/v1/router.py`

```python
# before
from app.api.v1 import evolutions, ingest, records, runs, search
router.include_router(records.router)

# after
from app.api.v1 import evolutions, ingest, runs, search, skills
router.include_router(skills.router)
```

---

### `backend/mcp_server.py`

6 URL strings updated:

| Before | After |
|--------|-------|
| `/api/v1/records/{skill_id}` | `/api/v1/skills/{skill_id}` |
| `/api/v1/records/{skill_id}/download` | `/api/v1/skills/{skill_id}/download` |

Affected tools: `tool_get_skill` (×2), `tool_execute_task` (×3), `tool_get_skill_lineage` (×1).

---

### `frontend/src/lib/api.ts`

4 URL strings updated:

| Before | After |
|--------|-------|
| `"/api/v1/records"` | `"/api/v1/skills"` |
| `` `/api/v1/records/${encodeURIComponent(recordId)}` `` | `` `/api/v1/skills/${encodeURIComponent(recordId)}` `` |
| `"/api/v1/records/metadata"` | `"/api/v1/skills/metadata"` |
| `` `/api/v1/records/${encodeURIComponent(recordId)}/download` `` | `` `/api/v1/skills/${encodeURIComponent(recordId)}/download` `` |

---

### `smoke-test.md`

8 curl examples updated: `$BASE/api/v1/records` → `$BASE/api/v1/skills`.  
Table entries: `POST /records` → `POST /skills`, `GET /records/...` → `GET /skills/...`.

---

### Test files

#### `backend/tests/integration/test_records.py`

3 route strings:
- `client.post("/api/v1/records", ...)` → `"/api/v1/skills"`
- `http_client.get("/api/v1/records/get_test_skill", ...)` → `"/api/v1/skills/get_test_skill"`
- `http_client.get("/api/v1/records/nonexistent", ...)` → `"/api/v1/skills/nonexistent"`

#### `backend/tests/integration/test_ingest.py`

2 route strings:
- `client.post("/api/v1/records", ...)` → `"/api/v1/skills"`
- `http_client.get(f"/api/v1/records/{skill_id}", ...)` → `"/api/v1/skills/{skill_id}"`

#### `backend/tests/integration/test_evolutions.py`

3 route strings:
- `client.post("/api/v1/records", ...)` → `"/api/v1/skills"`
- `http_client.get(f"/api/v1/records/{candidate_id}", ...)` → `"/api/v1/skills/{candidate_id}"`
- `http_client.get("/api/v1/records/lineage_child_v1", ...)` → `"/api/v1/skills/lineage_child_v1"`

---

## What did NOT change

- Database table name: `skill_records` — unchanged
- SQLAlchemy model class: `SkillRecord` — unchanged
- Pydantic schemas: `RecordResponse`, `CreateRecordRequest`, etc. — unchanged
- Business logic, deduplication, fingerprinting, embedding generation — all unchanged
- Frontend component names and TypeScript type names — unchanged
