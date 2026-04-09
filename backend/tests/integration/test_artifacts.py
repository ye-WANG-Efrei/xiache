"""T5 — POST /artifacts/stage integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import make_skill_md_bytes


async def _stage(client: AsyncClient, headers: dict, content: bytes = None,
                 filename: str = "SKILL.md") -> dict:
    if content is None:
        content = make_skill_md_bytes()
    resp = await client.post(
        "/api/v1/artifacts/stage",
        headers=headers,
        files=[("files", (filename, content, "text/plain"))],
    )
    return resp


# T5-1: 正常上传单个文件
async def test_stage_single_file(http_client, auth_headers):
    resp = await _stage(http_client, auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "artifact_id" in data
    assert len(data["artifact_id"]) == 36  # UUID format
    assert data["stats"]["file_count"] == 1
    assert data["stats"]["total_size"] > 0


# T5-2: 上传多文件
async def test_stage_multiple_files(http_client, auth_headers):
    resp = await http_client.post(
        "/api/v1/artifacts/stage",
        headers=auth_headers,
        files=[
            ("files", ("SKILL.md", make_skill_md_bytes(), "text/plain")),
            ("files", ("README.md", b"# Readme content here", "text/plain")),
        ],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["file_count"] == 2


# T5-3: 无文件 → 422
async def test_stage_no_files_returns_422(http_client, auth_headers):
    resp = await http_client.post("/api/v1/artifacts/stage", headers=auth_headers)
    assert resp.status_code == 422


# T5-4: 无 auth → 403
async def test_stage_no_auth_returns_403(http_client):
    resp = await http_client.post(
        "/api/v1/artifacts/stage",
        files=[("files", ("SKILL.md", make_skill_md_bytes(), "text/plain"))],
    )
    assert resp.status_code == 403


# T5-5: 相同文件上传两次 → 都返回 200，artifact_id 不同
async def test_stage_same_content_twice_gives_different_ids(http_client, auth_headers):
    content = make_skill_md_bytes()
    r1 = await _stage(http_client, auth_headers, content)
    r2 = await _stage(http_client, auth_headers, content)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["artifact_id"] != r2.json()["artifact_id"]
