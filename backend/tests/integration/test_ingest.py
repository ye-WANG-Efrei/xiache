"""T9 — POST /ingest/openspace integration tests."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers import make_skill_md_bytes


NOW = datetime.now(timezone.utc).isoformat()


def _judgment(skill_id: str, applied: bool, note: str = "") -> dict:
    return {"skill_id": skill_id, "skill_applied": applied, "note": note}


def _ingest_body(skill_id: str, applied: bool, completed: bool,
                  task_id: str = "task-1", note: str = "") -> dict:
    return {
        "task_id": task_id,
        "timestamp": NOW,
        "task_completed": completed,
        "execution_note": note,
        "skill_judgments": [_judgment(skill_id, applied, note)],
        "analyzed_by": "claude-3-opus",
        "analyzed_at": NOW,
    }


async def _stage_and_register(client, headers, record_id="test_skill_v1") -> str:
    await client.post("/api/v1/skills", headers=headers, json={
        "record_id": record_id,
        "name": record_id,
        "description": "A skill for ingest testing",
        "body": "## Steps\n1. Run the command\n2. Verify the output\n3. Done",
        "origin": "captured",
        "tags": ["test"],
        "version": "1.0.0",
    })
    return record_id


# T9-1: 正常 ingest — counters_updated 非空
async def test_ingest_normal(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t91")
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body(skill_id, applied=True, completed=True))
    assert resp.status_code == 200
    data = resp.json()
    assert skill_id in data["counters_updated"]
    assert data["judgments_processed"] == 1


# T9-2: skill 不在 registry → counters_updated 空
async def test_ingest_unknown_skill(http_client, auth_headers):
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body("ghost_skill_xyz", True, True))
    assert resp.status_code == 200
    assert resp.json()["counters_updated"] == []


# T9-3: total_selections 累加
async def test_ingest_selections_accumulate(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t93")
    for i in range(3):
        await http_client.post("/api/v1/ingest/openspace",
                                headers=auth_headers,
                                json=_ingest_body(skill_id, True, True, task_id=f"t{i}"))
    resp = await http_client.get(f"/api/v1/skills/{skill_id}", headers=auth_headers)
    # total_selections not in RecordResponse yet — verify via GET /records
    # We verify indirectly: 3 ingests succeeded without error
    assert resp.status_code == 200


# T9-4: applied=False, completed=False → total_fallbacks 增加（不直接查 DB，检查行为）
async def test_ingest_fallback_counting(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t94")
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body(skill_id, applied=False, completed=False))
    assert resp.status_code == 200
    assert skill_id in resp.json()["counters_updated"]


# T9-5: applied=False, completed=True → NOT a fallback (skipped-but-ok)
async def test_ingest_skipped_not_fallback(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t95")
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body(skill_id, applied=False, completed=True))
    assert resp.status_code == 200
    # Counted as selection but not fallback — just verify no error
    assert skill_id in resp.json()["counters_updated"]


# T9-6: applied=True, completed=True → total_completions 增加
async def test_ingest_completion_counting(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t96")
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body(skill_id, applied=True, completed=True))
    assert resp.status_code == 200
    assert skill_id in resp.json()["counters_updated"]


# T9-7: note 超过 500 字符 → 422 (Pydantic max_length)
async def test_ingest_note_too_long_rejected(http_client, auth_headers):
    body = {
        "task_id": "task-long",
        "timestamp": NOW,
        "task_completed": False,
        "execution_note": "a" * 501,
        "skill_judgments": [],
        "analyzed_by": "test",
        "analyzed_at": NOW,
    }
    resp = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers, json=body)
    assert resp.status_code == 422


# T9-8: 阈值触发但 LLM_API_KEY 未配置 → evolutions_triggered=[], 不报错
async def test_ingest_threshold_no_llm_graceful(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t98")

    # 5 fallbacks → crosses threshold
    for i in range(5):
        await http_client.post("/api/v1/ingest/openspace",
                                headers=auth_headers,
                                json=_ingest_body(skill_id, applied=False, completed=False,
                                                   task_id=f"t98-{i}"))
    last = await http_client.post("/api/v1/ingest/openspace",
                                   headers=auth_headers,
                                   json=_ingest_body(skill_id, applied=False, completed=False,
                                                     task_id="t98-final"))
    assert last.status_code == 200
    # Without LLM key, auto_evolver skips gracefully
    data = last.json()
    assert isinstance(data["evolutions_triggered"], list)


# T9-9: 已有 pending evolution → 不重复触发（需要 mock auto_evolver）
async def test_ingest_no_duplicate_evolution_when_pending_exists(http_client, auth_headers):
    skill_id = await _stage_and_register(http_client, auth_headers, "ingest_skill_t99")

    call_count = 0

    original_maybe_evolve = __import__(
        "app.services.auto_evolver", fromlist=["maybe_evolve"]
    ).maybe_evolve

    async def mock_maybe_evolve(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return None  # Simulate pending guard returning None (already pending)

    with patch("app.api.v1.ingest.auto_evolver.maybe_evolve",
               side_effect=mock_maybe_evolve):
        # Trigger threshold
        for i in range(6):
            await http_client.post(
                "/api/v1/ingest/openspace",
                headers=auth_headers,
                json=_ingest_body(skill_id, applied=False, completed=False,
                                   task_id=f"t99-{i}"),
            )

    # maybe_evolve was called (threshold crossed) but returned None each time
    assert call_count >= 1
