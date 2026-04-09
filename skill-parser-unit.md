# T1 — skill-parser 单元测试报告

**测试文件**: `backend/tests/unit/test_skill_parser.py`  
**被测模块**: `app/services/skill_parser.py`  
**运行日期**: 2026-04-09  
**结果**: 9/9 通过 ✅

---

## 测试单元

| 测试 ID | 测试名称 | 测试内容 | 预期结果 | 实际结果 |
|---------|----------|----------|----------|----------|
| T1-1 | `test_parse_full_frontmatter` | 完整 YAML frontmatter + body，包含 name/description/version/tags/input_schema/output_schema | 所有字段正确解析 | ✅ PASSED |
| T1-2 | `test_parse_missing_version` | SKILL.md 无 version 字段 | `version == ""` | ✅ PASSED |
| T1-3 | `test_parse_missing_tags` | SKILL.md 无 tags 字段 | `tags == []` | ✅ PASSED |
| T1-4 | `test_parse_tags_as_string` | tags 为逗号分隔字符串如 `"iot, demo, sensor"` | 正确拆分为列表 `["iot", "demo", "sensor"]` | ✅ PASSED |
| T1-5 | `test_parse_input_schema_not_dict` | `input_schema` 值为字符串而非 dict | 退回 `{}` | ✅ PASSED |
| T1-6 | `test_parse_no_skill_md` | ZIP 中无 SKILL.md 文件 | name/description/tags/body 全为空 | ✅ PASSED |
| T1-7 | `test_parse_bad_zip` | 输入非法 ZIP bytes | 不抛异常，version 退回 `"1.0.0"` | ✅ PASSED |
| T1-8 | `test_parse_skill_md_in_subdirectory` | SKILL.md 位于子目录（`subdir/SKILL.md`）| 仍能正确解析 name | ✅ PASSED |
| T1-9 | `test_parse_bad_yaml_frontmatter` | YAML frontmatter 语法错误（未闭合括号）| 不抛异常，name 为空字符串 | ✅ PASSED |

---

## 发现的 Bug 及修复

### Bug 1 — T1-2: 缺 version 时默认值错误
- **原代码**: `str(meta.get("version", "1.0.0"))` — 缺 version 时返回 `"1.0.0"`
- **测试期望**: 缺 version 字段时返回 `""`（空字符串）
- **修复**: 改为 `str(meta.get("version", ""))` — 让调用方或数据库层决定默认版本

### Bug 2 — T1-7: bad-zip 返回 dict 缺 key
- **原代码**: `{"name": "", "description": "", "tags": [], "body": ""}` — 无 `version`、`input_schema`、`output_schema`
- **影响**: 调用方访问 `result["version"]` 会触发 `KeyError`
- **修复**: 返回完整 dict，bad-zip 场景下 `version="1.0.0"`（表示"未知，使用默认"）

---

## 接口规范（parse_skill_md 的约定）

```python
parse_skill_md(zip_bytes: bytes) -> dict:
    # 正常返回
    {
        "name": str,         # 空字符串 if missing
        "description": str,  # 空字符串 if missing
        "version": str,      # 空字符串 if missing (bad-zip 时为 "1.0.0")
        "tags": list[str],   # 空列表 if missing or non-list
        "input_schema": dict, # 空 dict if missing or non-dict
        "output_schema": dict,# 空 dict if missing or non-dict
        "body": str,          # frontmatter 之后的正文
    }
    # 永不抛异常
```
