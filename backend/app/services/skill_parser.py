from __future__ import annotations

import io
import re
import zipfile
from typing import Any

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from markdown body.

    Returns (frontmatter_dict, body_text). If no frontmatter is found,
    returns ({}, original_text).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = m.group(2).strip()
    return meta, body


def parse_skill_md(zip_bytes: bytes) -> dict[str, Any]:
    """Extract SKILL.md from a ZIP archive and parse its frontmatter.

    Returns a dict with keys: name, description, tags, body.
    Falls back to empty strings / empty list if values are missing.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Accept SKILL.md at any depth; prefer root-level
            names = zf.namelist()
            skill_name = next(
                (n for n in names if n.split("/")[-1] == "SKILL.md"),
                None,
            )
            if skill_name is None:
                return {"name": "", "description": "", "version": "", "tags": [], "body": "",
                        "input_schema": {}, "output_schema": {}}
            raw = zf.read(skill_name).decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        return {"name": "", "description": "", "version": "1.0.0", "tags": [], "body": "",
                "input_schema": {}, "output_schema": {}}

    meta, body = _parse_frontmatter(raw)

    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    input_schema = meta.get("input_schema", {})
    if not isinstance(input_schema, dict):
        input_schema = {}

    output_schema = meta.get("output_schema", {})
    if not isinstance(output_schema, dict):
        output_schema = {}

    return {
        "name": str(meta.get("name", "")).strip(),
        "description": str(meta.get("description", "")).strip(),
        "version": str(meta.get("version", "")).strip(),
        "tags": [str(t) for t in tags],
        "input_schema": input_schema,
        "output_schema": output_schema,
        "body": body,
    }
