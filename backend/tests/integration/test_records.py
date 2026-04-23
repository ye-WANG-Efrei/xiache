"""T6 — POST /records integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import make_skill_md_bytes


async def _create_record(client, headers, record_id="test_skill_v1",
                          origin="captured", **kwargs) -> dict:
    body = {"record_id": record_id, "origin": origin, **kwargs}
    return await client.post("/api/v1/skills", headers=headers, json=body)


# T6-1: 正常创建 — 验证所有字段
async def test_create_record_happy_path(http_client, auth_headers):
    resp = await _create_record(
        http_client, auth_headers,
        record_id="blink_led_v1",
        name="blink_led_v1",
        description="Blink an LED on the target board",
        body="## Steps\n1. Connect LED\n2. Run blink script\n3. Verify LED blinks",
        tags=["iot"],
        version="2.0.0",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]
    assert data["version"] == "2.0.0"
    assert data["tags"] == ["iot"]
    assert isinstance(data["input_schema"], dict)
    assert isinstance(data["output_schema"], dict)
    assert data["origin"] == "captured"
    assert data["created_by"] == "dev"
    assert "content_fingerprint" in data


# T6-3: record_id + 内容相同 → 幂等 201
async def test_create_record_idempotent(http_client, auth_headers):
    kwargs = dict(
        record_id="idempotent_skill",
        name="Idempotent Skill",
        description="A skill for testing idempotency",
        body="## Steps\n1. Do the thing\n2. Verify the thing\n3. Done",
    )
    r1 = await _create_record(http_client, auth_headers, **kwargs)
    r2 = await _create_record(http_client, auth_headers, **kwargs)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["slug"] == r2.json()["slug"]


# T6-4: 同 record_id 不同内容 → 409
async def test_create_record_id_conflict_different_content(http_client, auth_headers):
    base = dict(
        record_id="conflict_skill",
        description="A conflict test skill",
        body="## Steps\n1. Do something\n2. Verify it\n3. Done",
    )
    r1 = await _create_record(http_client, auth_headers, name="Skill A", **base)
    r2 = await _create_record(http_client, auth_headers, name="Skill B", **base)
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"] == "record_id_fingerprint_conflict"


# T6-5: 同内容不同 record_id → 409
async def test_create_record_fingerprint_conflict(http_client, auth_headers):
    kwargs = dict(
        name="Same Content Skill",
        description="A skill with the same content",
        body="## Steps\n1. Do the same thing\n2. Verify it\n3. Done",
    )
    r1 = await _create_record(http_client, auth_headers, record_id="fp_skill_v1", **kwargs)
    r2 = await _create_record(http_client, auth_headers, record_id="fp_skill_v2", **kwargs)
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"] == "fingerprint_record_id_conflict"


# T6-7: GET /records/{id} 正常返回
async def test_get_record(http_client, auth_headers):
    await _create_record(
        http_client, auth_headers,
        record_id="get_test_skill",
        name="Get Test Skill",
        description="A skill for testing GET endpoint",
        body="## Steps\n1. Retrieve the skill\n2. Verify fields\n3. Done",
    )
    resp = await http_client.get("/api/v1/skills/get_test_skill", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == "get_test_skill"


# T6-8: GET /records/{id} 不存在 → 404
async def test_get_record_not_found(http_client, auth_headers):
    resp = await http_client.get("/api/v1/skills/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
