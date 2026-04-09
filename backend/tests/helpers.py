"""Shared test helpers — zip builders, fixture data."""
from __future__ import annotations

import io
import zipfile


GOOD_BODY = """\
## Steps
1. Validate input parameters carefully
2. Execute the core logic
3. Handle errors gracefully
4. Return structured result
"""

DANGEROUS_BODY = """\
## Steps
1. drop table skill_records;
2. Return result
"""

DANGEROUS_BODY_UPPERCASE = """\
## Steps
1. DROP TABLE skill_records;
2. Return result
"""


def make_skill_md(
    name: str = "Test Skill Alpha",
    description: str = "A comprehensive test skill for automated testing",
    version: str = "1.0.0",
    tags: list[str] | None = None,
    body: str = GOOD_BODY,
    extra_frontmatter: str = "",
) -> str:
    if tags is None:
        tags = ["test"]
    tags_yaml = "\n".join(f"  - {t}" for t in tags)
    return f"""---
name: {name}
description: {description}
version: {version}
tags:
{tags_yaml}
input_schema:
  type: object
  properties:
    value: {{type: string}}
output_schema:
  type: object
  properties:
    result: {{type: string}}
{extra_frontmatter}
---

{body}"""


def make_skill_zip(
    name: str = "Test Skill Alpha",
    description: str = "A comprehensive test skill for automated testing",
    version: str = "1.0.0",
    tags: list[str] | None = None,
    body: str = GOOD_BODY,
    extra_files: dict[str, str] | None = None,
) -> bytes:
    """Return a ZIP containing SKILL.md (and optional extra files)."""
    skill_md = make_skill_md(name=name, description=description,
                              version=version, tags=tags, body=body)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SKILL.md", skill_md.encode())
        if extra_files:
            for fname, content in extra_files.items():
                zf.writestr(fname, content.encode())
    return buf.getvalue()


def make_skill_md_bytes(
    name: str = "Test Skill Alpha",
    description: str = "A comprehensive test skill for automated testing",
    version: str = "1.0.0",
    tags: list[str] | None = None,
    body: str = GOOD_BODY,
) -> bytes:
    """Return raw SKILL.md bytes (for multipart upload to /artifacts/stage)."""
    return make_skill_md(name=name, description=description,
                         version=version, tags=tags, body=body).encode()
