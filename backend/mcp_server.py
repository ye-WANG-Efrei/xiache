"""
xiache MCP Server
=================
Exposes the xiache skill platform as MCP tools so any MCP-compatible
agent (Claude, Claw, etc.) can discover and use skills directly.

7 core tools (per architectbyOpenspace.md §9):
  search_skills         — semantic + hardware-aware search
  get_skill             — full skill content (SKILL.md + skill.yaml)
  execute_task          — reasoning executor (Phase 1)
  submit_skill_revision — propose a fix/derive evolution
  publish_skill         — publish a brand-new captured skill
  get_skill_lineage     — ancestry + descendants graph
  get_execution_log     — execution run details

Usage:
  python mcp_server.py

Environment (reads from ../.env or .env):
  XIACHE_API_URL   — default http://localhost:8000
  XIACHE_API_KEY   — default dev-key-for-testing
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Load .env from mcp_server.py location or parent
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

API_URL = os.getenv("XIACHE_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("XIACHE_API_KEY", os.getenv("DEV_API_KEY", "dev-key-for-testing"))

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}", headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()


async def _post_multipart(path: str, files_content: dict[str, str]) -> Any:
    """Upload text files as multipart form."""
    async with httpx.AsyncClient(timeout=30) as client:
        files = [
            ("files", (name, content.encode(), "text/plain"))
            for name, content in files_content.items()
        ]
        r = await client.post(
            f"{API_URL}{path}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
        )
        r.raise_for_status()
        return r.json()


async def _download_bytes(path: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{API_URL}{path}",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        r.raise_for_status()
        return r.content


def _ok(data: Any) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
    )


def _err(msg: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=f"ERROR: {msg}")],
        isError=True,
    )

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def tool_search_skills(
    query: str,
    limit: int = 10,
    domain: str | None = None,
    risk_level: str | None = None,
) -> CallToolResult:
    """Search skills by natural-language query with optional filters."""
    try:
        params: dict = {"q": query, "limit": limit}
        if domain:
            params["domain"] = domain
        if risk_level:
            params["risk_level"] = risk_level
        data = await _get("/api/v1/search", params)
        # Return concise result
        results = [
            {
                "skill_id": r["record_id"],
                "name": r["name"],
                "description": r["description"],
                "tags": r["tags"],
                "risk_level": r.get("risk_level", "low"),
                "score": round(r["score"], 4),
            }
            for r in data.get("results", [])
        ]
        return _ok({
            "query": query,
            "count": data.get("count", 0),
            "search_type": data.get("search_type"),
            "results": results,
        })
    except Exception as e:
        return _err(str(e))


async def tool_get_skill(skill_id: str) -> CallToolResult:
    """Get the full content of a skill: metadata + SKILL.md text."""
    try:
        meta = await _get(f"/api/v1/skills/{skill_id}")
        # Try to download and extract SKILL.md text
        skill_text = None
        yaml_text = None
        try:
            zip_bytes = await _download_bytes(f"/api/v1/skills/{skill_id}/download")
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    if name.endswith("SKILL.md"):
                        skill_text = zf.read(name).decode("utf-8", errors="replace")
                    elif name.endswith("skill.yaml"):
                        yaml_text = zf.read(name).decode("utf-8", errors="replace")
        except Exception:
            pass

        return _ok({
            "skill_id": meta["record_id"],
            "name": meta["name"],
            "description": meta["description"],
            "origin": meta["origin"],
            "tags": meta["tags"],
            "created_by": meta["created_by"],
            "parent_skill_ids": meta["parent_skill_ids"],
            "skill_md": skill_text or "(not available)",
            "skill_yaml": yaml_text or "(not available)",
        })
    except Exception as e:
        return _err(str(e))


async def tool_execute_task(
    task: str,
    skill_id: str | None = None,
    context: dict | None = None,
    target_env: dict | None = None,
) -> CallToolResult:
    """
    Execute a task using the reasoning executor (Phase 1).

    Searches for a matching skill, logs the execution run, and returns
    the skill's instructions for the agent to follow.

    In Phase 1, actual execution is performed by the agent itself guided
    by the skill content. The platform records the run for lineage.
    """
    try:
        # Step 1: find the skill
        if skill_id:
            skill_data = await _get(f"/api/v1/skills/{skill_id}")
        else:
            search = await _get("/api/v1/search", {"q": task, "limit": 1})
            results = search.get("results", [])
            if not results:
                return _ok({
                    "status": "no_skill_found",
                    "message": (
                        "No matching skill found. Consider publishing one with "
                        "publish_skill after completing this task manually."
                    ),
                    "task": task,
                })
            skill_data = await _get(f"/api/v1/skills/{results[0]['record_id']}")
            skill_id = skill_data["record_id"]

        # Step 2: get skill content
        skill_text = ""
        try:
            zip_bytes = await _download_bytes(f"/api/v1/skills/{skill_id}/download")
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    if name.endswith("SKILL.md"):
                        skill_text = zf.read(name).decode("utf-8", errors="replace")
        except Exception:
            pass

        # Step 3: log the run
        run_body = {
            "skill_id": skill_id,
            "task": task,
            "executor_type": "reasoning",
            "target_env": target_env or {},
            "context": context or {},
        }
        try:
            run = await _post("/api/v1/runs", run_body)
            run_id = run.get("run_id")
        except Exception:
            run_id = None

        return _ok({
            "status": "executing",
            "run_id": run_id,
            "skill_id": skill_id,
            "skill_name": skill_data["name"],
            "task": task,
            "instructions": skill_text or skill_data["description"],
            "note": (
                "Follow the instructions above to complete the task. "
                "When done, report success or failure so the run can be closed."
            ),
        })
    except Exception as e:
        return _err(str(e))


async def tool_submit_skill_revision(
    skill_id: str,
    skill_md: str,
    rationale: str,
    skill_yaml: str | None = None,
) -> CallToolResult:
    """
    Propose a fix or improvement to an existing skill (origin: fixed).

    Provide the complete revised SKILL.md content and a rationale.
    The platform evaluates it automatically; if quality score >= threshold
    it is published immediately, otherwise it enters review queue.
    """
    try:
        evo = await _post("/api/v1/evolutions", {
            "name": skill_id,
            "description": rationale[:200] if rationale else "",
            "body": skill_md,
            "parent_skill_id": skill_id,
            "origin": "fixed",
            "change_summary": rationale,
        })

        return _ok({
            "evolution_id": evo["evolution_id"],
            "status": evo["status"],
            "auto_accepted": evo["auto_accepted"],
            "result_skill_id": evo.get("result_record_id"),
            "evaluation": evo.get("evaluation"),
            "message": (
                "Revision auto-published." if evo["auto_accepted"]
                else f"Revision queued for review (status: {evo['status']}). "
                     f"Feedback: {evo.get('evaluation', {}).get('notes', '')}"
            ),
        })
    except Exception as e:
        return _err(str(e))


async def tool_publish_skill(
    name: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    skill_yaml: str | None = None,
) -> CallToolResult:
    """
    Publish a brand-new skill captured from experience (origin: captured).

    Provide name, description, and the full instructional body.
    The platform evaluates, and if it passes, publishes immediately.
    """
    try:
        evo = await _post("/api/v1/evolutions", {
            "name": name,
            "description": description,
            "body": body,
            "origin": "captured",
            "tags": tags or [],
        })

        return _ok({
            "evolution_id": evo["evolution_id"],
            "status": evo["status"],
            "skill_id": evo.get("result_record_id"),
            "auto_accepted": evo["auto_accepted"],
            "evaluation": evo.get("evaluation"),
            "message": (
                f"Skill '{name}' published successfully."
                if evo["auto_accepted"]
                else f"Skill '{name}' queued for review. "
                     f"Feedback: {evo.get('evaluation', {}).get('notes', '')}"
            ),
        })
    except Exception as e:
        return _err(str(e))


async def tool_get_skill_lineage(skill_id: str) -> CallToolResult:
    """Get ancestry and evolution history of a skill."""
    try:
        meta = await _get(f"/api/v1/skills/{skill_id}")
        evolutions = await _get("/api/v1/evolutions", {
            "parent_skill_id": skill_id,
            "limit": 50,
        })

        return _ok({
            "skill_id": skill_id,
            "name": meta["name"],
            "origin": meta["origin"],
            "parents": meta["parent_skill_ids"],
            "children": [
                {
                    "evolution_id": e["evolution_id"],
                    "status": e["status"],
                    "result_skill_id": e.get("result_record_id"),
                    "change_summary": e["change_summary"],
                    "proposed_at": e["proposed_at"],
                    "auto_accepted": e["auto_accepted"],
                }
                for e in evolutions.get("items", [])
            ],
            "total_evolutions": evolutions.get("total", 0),
        })
    except Exception as e:
        return _err(str(e))


async def tool_get_execution_log(run_id: str) -> CallToolResult:
    """Get details and logs of an execution run."""
    try:
        run = await _get(f"/api/v1/runs/{run_id}")
        return _ok(run)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="search_skills",
        description=(
            "Search for skills on the xiache platform by natural-language query. "
            "Optionally filter by domain (e.g. 'embedded', 'ota') or risk_level "
            "('low', 'medium', 'high'). Returns ranked skill IDs and descriptions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query":      {"type": "string", "description": "Natural-language search query"},
                "limit":      {"type": "integer", "default": 10, "description": "Max results"},
                "domain":     {"type": "string", "description": "Domain filter, e.g. 'embedded'"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_skill",
        description=(
            "Fetch the full content of a skill by ID, including its SKILL.md "
            "instructions and skill.yaml structured spec."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill record ID"},
            },
            "required": ["skill_id"],
        },
    ),
    Tool(
        name="execute_task",
        description=(
            "Execute a task using the xiache reasoning executor. "
            "Finds the best matching skill, returns its instructions, "
            "and logs the execution run for lineage tracking. "
            "Provide skill_id to skip search and use a specific skill."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task":       {"type": "string", "description": "Task description"},
                "skill_id":   {"type": "string", "description": "Specific skill to use (optional)"},
                "context":    {"type": "object", "description": "Additional context"},
                "target_env": {
                    "type": "object",
                    "description": "Target environment, e.g. {board_type: 'stm32', interface: 'uart'}",
                },
            },
            "required": ["task"],
        },
    ),
    Tool(
        name="submit_skill_revision",
        description=(
            "Propose a fix or improvement to an existing skill (origin: fixed). "
            "Provide the complete revised SKILL.md content and a rationale. "
            "If the revision passes automated quality checks it is published immediately; "
            "otherwise it enters the review queue with feedback."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "skill_id":   {"type": "string", "description": "ID of the skill to revise"},
                "skill_md":   {"type": "string", "description": "Complete revised SKILL.md content"},
                "rationale":  {"type": "string", "description": "Why this revision is needed"},
                "skill_yaml": {"type": "string", "description": "Optional revised skill.yaml"},
            },
            "required": ["skill_id", "skill_md", "rationale"],
        },
    ),
    Tool(
        name="publish_skill",
        description=(
            "Publish a brand-new skill captured from experience. "
            "Provide a name, description, and the full instructional body. "
            "The platform evaluates it and publishes if it passes quality checks."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name":        {"type": "string", "description": "Short skill name (kebab-case)"},
                "description": {"type": "string", "description": "One-line description (>=10 chars)"},
                "body":        {"type": "string", "description": "Full instructional content (>=20 chars)"},
                "tags":        {"type": "array", "items": {"type": "string"}},
                "skill_yaml":  {"type": "string", "description": "Optional structured skill.yaml spec"},
            },
            "required": ["name", "description", "body"],
        },
    ),
    Tool(
        name="get_skill_lineage",
        description=(
            "Get the evolution history and lineage of a skill: "
            "its parents, all proposed/accepted revisions, and their outcomes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
            },
            "required": ["skill_id"],
        },
    ),
    Tool(
        name="get_execution_log",
        description="Get the details and logs of a specific execution run by run_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
            },
            "required": ["run_id"],
        },
    ),
]

TOOL_HANDLERS = {
    "search_skills":         tool_search_skills,
    "get_skill":             tool_get_skill,
    "execute_task":          tool_execute_task,
    "submit_skill_revision": tool_submit_skill_revision,
    "publish_skill":         tool_publish_skill,
    "get_skill_lineage":     tool_get_skill_lineage,
    "get_execution_log":     tool_get_execution_log,
}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("xiache")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    result = await handler(**arguments)
    return result.content


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
