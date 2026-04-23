"""T7/T8 — evolutions integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import DANGEROUS_BODY, GOOD_BODY


async def _create_record(client, headers, record_id, name=None, origin="captured") -> None:
    resp = await client.post("/api/v1/skills", headers=headers, json={
        "record_id": record_id,
        "name": name or record_id,
        "description": "A skill for evolution testing",
        "body": GOOD_BODY,
        "origin": origin,
        "tags": ["test"],
        "version": "1.0.0",
    })
    assert resp.status_code == 201


async def _propose(client, headers, name="Test Skill", description="A test skill for evolution",
                   body=None, parent_skill_id=None, candidate_skill_id=None,
                   origin="captured", change_summary="", tags=None,
                   version="1.0.0") -> dict:
    payload = {
        "name": name,
        "description": description,
        "body": body or GOOD_BODY,
        "origin": origin,
        "change_summary": change_summary,
        "tags": tags or ["test"],
        "version": version,
    }
    if parent_skill_id:
        payload["parent_skill_id"] = parent_skill_id
    if candidate_skill_id:
        payload["candidate_skill_id"] = candidate_skill_id
    return await client.post("/api/v1/evolutions", headers=headers, json=payload)


# ---------------------------------------------------------------------------
# T7: Evolution 提交
# ---------------------------------------------------------------------------

# T7-1: 完美 captured skill → auto-accepted
async def test_evolution_captured_auto_accepted(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers,
                           name="Perfect Skill",
                           candidate_skill_id="perfect_skill_v1")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["auto_accepted"] is True
    assert data["result_record_id"] == "perfect_skill_v1"
    assert data["evaluation"]["quality_score"] == 1.0


# T7-2: 完美 fixed skill（parent 存在）→ auto-accepted
async def test_evolution_fixed_auto_accepted(http_client, auth_headers):
    await _create_record(http_client, auth_headers, "parent_skill_v1", name="Parent Skill")

    resp = await _propose(http_client, auth_headers,
                           name="Parent Skill",
                           body=GOOD_BODY + "\n5. Extra step added here",
                           version="1.0.1",
                           parent_skill_id="parent_skill_v1",
                           candidate_skill_id="parent_skill_v2",
                           origin="fixed",
                           change_summary="added extra validation step here")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["result_record_id"] == "parent_skill_v2"
    assert data["evaluation"]["checks"]["parent_exists"] is True
    assert data["evaluation"]["checks"]["lineage_valid"] is True


# T7-3: parent 不存在 → rejected
async def test_evolution_fixed_parent_not_found(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers,
                           parent_skill_id="ghost_skill_v999",
                           origin="fixed",
                           change_summary="fixing the ghost skill step")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["evaluation"]["checks"]["parent_exists"] is False


# T7-4: 重复内容 → rejected (not_duplicate 硬拦截)
async def test_evolution_duplicate_content_rejected(http_client, auth_headers):
    await _create_record(http_client, auth_headers, "dup_skill_v1", name="Duplicate Skill")

    resp = await _propose(http_client, auth_headers,
                           name="Duplicate Skill",
                           candidate_skill_id="dup_skill_v2")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["evaluation"]["checks"]["not_duplicate"] is False


# T7-5: candidate_skill_id 碰撞已有 record → 409
async def test_evolution_candidate_id_collision(http_client, auth_headers):
    await _create_record(http_client, auth_headers, "existing_skill", name="Existing Skill")

    resp = await _propose(http_client, auth_headers,
                           name="New Skill Attempt",
                           body=GOOD_BODY + "\n# different content",
                           candidate_skill_id="existing_skill")
    assert resp.status_code == 409


# T7-6: body 太短 → pending or rejected (score too low)
async def test_evolution_short_body_low_score(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers, body="short")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("rejected", "pending")
    assert data["evaluation"]["checks"]["has_body"] is False


# T7-7/8: 危险代码 → rejected (大小写都拦截)
async def test_evolution_dangerous_body_uppercase_rejected(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers, body="DROP TABLE skill_records; do thing")
    assert resp.status_code == 201
    assert resp.json()["status"] == "rejected"
    assert resp.json()["evaluation"]["checks"]["no_dangerous_patterns"] is False


async def test_evolution_dangerous_body_lowercase_rejected(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers, body="drop table skill_records; do thing")
    assert resp.status_code == 201
    assert resp.json()["status"] == "rejected"
    assert resp.json()["evaluation"]["checks"]["no_dangerous_patterns"] is False


# ---------------------------------------------------------------------------
# T8: 手动 Accept / Reject
# ---------------------------------------------------------------------------

async def _create_pending_evolution(client, headers) -> tuple[str, str]:
    """Returns (evolution_id, candidate_skill_id) for a pending evolution."""
    resp = await _propose(client, headers,
                           name="Pending Test Skill",
                           description="short",
                           body="short body",
                           tags=[],
                           candidate_skill_id="pending_skill_v1")
    data = resp.json()
    assert data["status"] == "pending", f"Expected pending, got {data['status']}: {data}"
    return data["evolution_id"], "pending_skill_v1"


# T8-1: accept pending → accepted
async def test_manual_accept_pending(http_client, auth_headers):
    evo_id, candidate_id = await _create_pending_evolution(http_client, auth_headers)
    resp = await http_client.post(f"/api/v1/evolutions/{evo_id}/accept",
                                   headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["result_record_id"] == candidate_id
    assert data["auto_accepted"] is False


# T8-2: accept 已 accepted → 409
async def test_accept_already_accepted_returns_409(http_client, auth_headers):
    resp = await _propose(http_client, auth_headers,
                           name="Already Accepted Skill",
                           candidate_skill_id="already_accepted_skill")
    evo_id = resp.json()["evolution_id"]
    assert resp.json()["status"] == "accepted"

    resp2 = await http_client.post(f"/api/v1/evolutions/{evo_id}/accept",
                                    headers=auth_headers)
    assert resp2.status_code == 409


# T8-3: reject pending → rejected + reason in notes
async def test_manual_reject_pending(http_client, auth_headers):
    evo_id, _ = await _create_pending_evolution(http_client, auth_headers)
    resp = await http_client.post(f"/api/v1/evolutions/{evo_id}/reject",
                                   headers=auth_headers,
                                   json={"reason": "skill quality insufficient for production"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "skill quality insufficient" in data["evaluation"]["notes"]


# T8-4: reject 已 rejected → 409
async def test_reject_already_rejected_returns_409(http_client, auth_headers):
    evo_id, _ = await _create_pending_evolution(http_client, auth_headers)
    await http_client.post(f"/api/v1/evolutions/{evo_id}/reject",
                            headers=auth_headers,
                            json={"reason": "first rejection"})
    resp = await http_client.post(f"/api/v1/evolutions/{evo_id}/reject",
                                   headers=auth_headers,
                                   json={"reason": "second rejection"})
    assert resp.status_code == 409


# T8-5: accept 后 record 存在
async def test_record_exists_after_accept(http_client, auth_headers):
    evo_id, candidate_id = await _create_pending_evolution(http_client, auth_headers)
    await http_client.post(f"/api/v1/evolutions/{evo_id}/accept", headers=auth_headers)

    resp = await http_client.get(f"/api/v1/skills/{candidate_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == candidate_id


# T8-6: accept 后血缘关系存在（fixed origin）
async def test_lineage_exists_after_fixed_accept(http_client, auth_headers):
    await _create_record(http_client, auth_headers, "lineage_parent_v1",
                          name="Lineage Parent")

    resp = await _propose(http_client, auth_headers,
                           name="Lineage Child",
                           description="short",
                           body="child body short text here",
                           tags=[],
                           version="1.0.1",
                           parent_skill_id="lineage_parent_v1",
                           candidate_skill_id="lineage_child_v1",
                           origin="fixed",
                           change_summary="fixing the child step logic")
    evo_id = resp.json()["evolution_id"]

    if resp.json()["status"] == "pending":
        await http_client.post(f"/api/v1/evolutions/{evo_id}/accept",
                                headers=auth_headers)

    child_resp = await http_client.get("/api/v1/skills/lineage_child_v1",
                                        headers=auth_headers)
    assert child_resp.status_code == 200
    assert "lineage_parent_v1" in child_resp.json()["parent_skill_ids"]
