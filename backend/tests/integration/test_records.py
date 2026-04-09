"""T6 — POST /records integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import make_skill_md_bytes


async def _stage(client: AsyncClient, headers: dict, content: bytes = None) -> str:
    if content is None:
        content = make_skill_md_bytes()
    resp = await client.post(
        "/api/v1/artifacts/stage",
        headers=headers,
        files=[("files", ("SKILL.md", content, "text/plain"))],
    )
    assert resp.status_code == 200
    return resp.json()["artifact_id"]


async def _create_record(client, headers, record_id="test_skill_v1",
                          artifact_id=None, origin="captured", **kwargs) -> dict:
    body = {"record_id": record_id, "artifact_id": artifact_id, "origin": origin, **kwargs}
    return await client.post("/api/v1/records", headers=headers, json=body)


# T6-1: 正常创建 — 验证所有新字段
async def test_create_record_happy_path(http_client, auth_headers):
    artifact_id = await _stage(http_client, auth_headers,
                                make_skill_md_bytes(version="2.0.0", tags=["iot"]))
    resp = await _create_record(http_client, auth_headers,
                                 record_id="blink_led_v1", artifact_id=artifact_id)
    assert resp.status_code == 201
    data = resp.json()

    assert data["record_id"] == "blink_led_v1"
    assert data["artifact_ref"] == "artifact://blink_led_v1"
    assert data["version"] == "2.0.0"
    assert data["tags"] == ["iot"]
    assert isinstance(data["input_schema"], dict)
    assert isinstance(data["output_schema"], dict)
    assert data["origin"] == "captured"
    assert data["created_by"] == "dev"
    assert "content_fingerprint" in data


# T6-2: artifact 不存在 → 404
async def test_create_record_artifact_not_found(http_client, auth_headers):
    resp = await _create_record(http_client, auth_headers,
                                 artifact_id="00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# T6-3: record_id + 内容相同 → 幂等 201
async def test_create_record_idempotent(http_client, auth_headers):
    content = make_skill_md_bytes()
    artifact_id = await _stage(http_client, auth_headers, content)
    r1 = await _create_record(http_client, auth_headers,
                               record_id="idempotent_skill", artifact_id=artifact_id)
    # Stage same content again (same fingerprint, different artifact row)
    artifact_id2 = await _stage(http_client, auth_headers, content)
    r2 = await _create_record(http_client, auth_headers,
                               record_id="idempotent_skill", artifact_id=artifact_id2)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["record_id"] == r2.json()["record_id"]


# T6-4: 同 record_id 不同内容 → 409
async def test_create_record_id_conflict_different_content(http_client, auth_headers):
    a1 = await _stage(http_client, auth_headers, make_skill_md_bytes(name="Skill A"))
    a2 = await _stage(http_client, auth_headers, make_skill_md_bytes(name="Skill B"))
    r1 = await _create_record(http_client, auth_headers,
                               record_id="conflict_skill", artifact_id=a1)
    r2 = await _create_record(http_client, auth_headers,
                               record_id="conflict_skill", artifact_id=a2)
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"] == "record_id_fingerprint_conflict"


# T6-5: 同内容不同 record_id → 409
async def test_create_record_fingerprint_conflict(http_client, auth_headers):
    content = make_skill_md_bytes(name="Same Content")
    a1 = await _stage(http_client, auth_headers, content)
    a2 = await _stage(http_client, auth_headers, content)
    r1 = await _create_record(http_client, auth_headers,
                               record_id="fp_skill_v1", artifact_id=a1)
    r2 = await _create_record(http_client, auth_headers,
                               record_id="fp_skill_v2", artifact_id=a2)
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"] == "fingerprint_record_id_conflict"


# T6-6: version/tags 从 SKILL.md 解析，不依赖请求体默认值
async def test_record_reads_version_from_skill_md(http_client, auth_headers):
    content = make_skill_md_bytes(version="3.5.1", tags=["alpha", "beta"])
    artifact_id = await _stage(http_client, auth_headers, content)
    resp = await _create_record(http_client, auth_headers,
                                 record_id="versioned_skill", artifact_id=artifact_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "3.5.1"
    assert "alpha" in data["tags"]
    assert "beta" in data["tags"]


# T6-7: GET /records/{id} 正常返回
async def test_get_record(http_client, auth_headers):
    artifact_id = await _stage(http_client, auth_headers)
    await _create_record(http_client, auth_headers,
                          record_id="get_test_skill", artifact_id=artifact_id)
    resp = await http_client.get("/api/v1/records/get_test_skill", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["record_id"] == "get_test_skill"


# T6-8: GET /records/{id} 不存在 → 404
async def test_get_record_not_found(http_client, auth_headers):
    resp = await http_client.get("/api/v1/records/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
