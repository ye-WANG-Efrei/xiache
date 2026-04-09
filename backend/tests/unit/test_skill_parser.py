"""T1 — skill_parser.parse_skill_md unit tests."""
from __future__ import annotations

import io
import zipfile

import pytest

from tests.helpers import make_skill_zip, make_skill_md
from app.services.skill_parser import parse_skill_md


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content.encode())
    return buf.getvalue()


# T1-1: 完整 frontmatter 正常解析
def test_parse_full_frontmatter():
    z = make_skill_zip(
        name="Blink LED",
        description="blink led once when triggered",
        version="2.1.0",
        tags=["iot", "demo"],
    )
    result = parse_skill_md(z)
    assert result["name"] == "Blink LED"
    assert result["description"] == "blink led once when triggered"
    assert result["version"] == "2.1.0"
    assert result["tags"] == ["iot", "demo"]
    assert isinstance(result["input_schema"], dict)
    assert isinstance(result["output_schema"], dict)
    assert len(result["body"]) > 0


# T1-2: 缺 version 字段
def test_parse_missing_version():
    md = "---\nname: No Version\ndescription: test description here\ntags:\n  - test\n---\n\nbody text here"
    z = _zip({"SKILL.md": md})
    result = parse_skill_md(z)
    assert result["version"] == ""


# T1-3: 缺 tags
def test_parse_missing_tags():
    md = "---\nname: No Tags\ndescription: test description here\nversion: 1.0.0\n---\n\nbody"
    z = _zip({"SKILL.md": md})
    result = parse_skill_md(z)
    assert result["tags"] == []


# T1-4: tags 是逗号分隔字符串
def test_parse_tags_as_string():
    md = '---\nname: Tags Test\ndescription: test description here\nversion: 1.0.0\ntags: "iot, demo, sensor"\n---\n\nbody'
    z = _zip({"SKILL.md": md})
    result = parse_skill_md(z)
    assert result["tags"] == ["iot", "demo", "sensor"]


# T1-5: input_schema 非 dict → 退回空 dict
def test_parse_input_schema_not_dict():
    md = '---\nname: Schema Test\ndescription: test description here\nversion: 1.0.0\ntags:\n  - test\ninput_schema: "wrong"\n---\n\nbody'
    z = _zip({"SKILL.md": md})
    result = parse_skill_md(z)
    assert result["input_schema"] == {}


# T1-6: ZIP 中没有 SKILL.md
def test_parse_no_skill_md():
    z = _zip({"README.md": "# Hello"})
    result = parse_skill_md(z)
    assert result["name"] == ""
    assert result["description"] == ""
    assert result["tags"] == []
    assert result["body"] == ""


# T1-7: 非法 ZIP bytes → 不抛异常，返回空默认值
def test_parse_bad_zip():
    result = parse_skill_md(b"this is not a zip file at all")
    assert result["name"] == ""
    assert result["version"] == "1.0.0"  # default fallback


# T1-8: SKILL.md 在子目录里也能找到
def test_parse_skill_md_in_subdirectory():
    z = _zip({"subdir/SKILL.md": make_skill_md(name="Sub Skill")})
    result = parse_skill_md(z)
    assert result["name"] == "Sub Skill"


# T1-9: YAML frontmatter 损坏 → 返回空 meta，不抛异常
def test_parse_bad_yaml_frontmatter():
    md = "---\nname: [unclosed bracket\n---\n\nbody content here"
    z = _zip({"SKILL.md": md})
    result = parse_skill_md(z)
    # Should not raise, name may be empty
    assert isinstance(result["name"], str)
