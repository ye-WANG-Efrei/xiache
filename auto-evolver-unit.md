# T3/T4 — auto-evolver 单元测试报告

**测试文件**: `backend/tests/unit/test_auto_evolver.py`  
**被测模块**: `app/services/auto_evolver.py`  
**运行日期**: 2026-04-09  
**结果**: 19/19 通过 ✅  
（注：`should_evolve` 的测试编号为 T5 但仍在同一测试文件中）

---

## T3 — `_bump_patch` 版本号递增

| 测试 ID | 测试名称 | 输入 | 预期输出 | 实际结果 |
|---------|----------|------|----------|----------|
| T3-1 | `test_bump_patch_basic` | `"1.0.0"` | `"1.0.1"` | ✅ PASSED |
| T3-2 | `test_bump_patch_large_patch` | `"2.3.9"` | `"2.3.10"` | ✅ PASSED |
| T3-3 | `test_bump_patch_prerelease_strips_suffix` | `"1.0.3-beta.1"` | `"1.0.4"` (valid semver) | ✅ PASSED |
| T3-4 | `test_bump_patch_build_metadata` | `"1.0.0+build.1"` | `"1.0.1"` (valid semver) | ✅ PASSED |
| T3-5 | `test_bump_patch_prerelease_and_build` | `"1.0.3-beta.1+build"` | `"1.0.4"` (valid semver) | ✅ PASSED |
| T3-6 | `test_bump_patch_two_segments_fallback` | `"1.0"` | 以 `"1.0"` 开头（降级处理）| ✅ PASSED |
| T3-7 | `test_bump_patch_result_always_valid_semver_for_standard_input` | 多个标准 semver 字符串 | 每个输出均为合法 semver | ✅ PASSED |

### Bug 发现 — T3-4: build metadata 未被剥离
- **原代码**: `parts[2].split("-")[0]` — 对 `"1.0.0+build.1"` 得到 `"0+build"`，`"0+build".isdigit()` 为 False，走 fallback → `"1.0.0+build.1.1"`（非法）
- **修复**: 改为 `parts[2].split("-")[0].split("+")[0]` — 先去掉 pre-release，再去掉 build metadata

---

## T4 — `_sanitize_notes` 注入防护

| 测试 ID | 测试名称 | 输入 | 预期行为 | 实际结果 |
|---------|----------|------|----------|----------|
| T4-1 | `test_sanitize_normal_note_unchanged` | 普通字符串 38 字符 | 原样返回 | ✅ PASSED |
| T4-2 | `test_sanitize_truncates_at_500` | 1000 字符字符串 | 截断至 500 字符 | ✅ PASSED |
| T4-3 | `test_sanitize_escapes_closing_xml_tag` | 含 `</execution_failure_notes>` | `</` → `<\/`，无 `</` 残留 | ✅ PASSED |
| T4-4 | `test_sanitize_truncate_then_escape` | `"a" * 498 + "</x>"` (502 chars) | 结果 ≤ 500 字符，无 `</` | ✅ PASSED |
| T4-5 | `test_sanitize_multiple_notes` | 列表含短/长/短三条 | 长条截断，列表长度保持 3 | ✅ PASSED |
| T4-6 | `test_sanitize_empty_list` | `[]` | `[]` | ✅ PASSED |

### Bug 发现 — T4-4: 先截断后转义导致超长
- **原代码**: `n[:500].replace("</", "<\\/")` — 输入 `"a"*498 + "</x>"`，截断到 `"a"*498 + "</"` (500 chars)，转义 `</` → `<\/` 得到 501 字符
- **修复**: `n.replace("</", "<\\/")[:500]` — 先转义再截断，保证结果 ≤ 500 字符
- **安全意义**: `</execution_failure_notes>` 可用于注入 XML 标签闭合 LLM prompt，转义必须在截断前完成

---

## T5 — `should_evolve` 进化阈值判断

| 测试 ID | 测试名称 | 场景 | 预期 | 实际结果 |
|---------|----------|------|------|----------|
| T5-1 | `test_not_enough_data` | selections=3（低于最小 5）| `False`, "not enough data" | ✅ PASSED |
| T5-2 | `test_high_fallback_rate_triggers` | fallback_rate=0.6 > 0.4 | `True`, "fallback_rate" | ✅ PASSED |
| T5-3 | `test_low_completion_rate_triggers` | completion_rate=0.2 < 0.35 | `True`, "completion_rate" | ✅ PASSED |
| T5-4 | `test_good_metrics_no_trigger` | fallback=0, completion=0.89 | `False`, "OK" | ✅ PASSED |
| T5-5 | `test_exact_fallback_threshold_boundary` | fallback_rate=0.40 整（临界值）| `False`（`>` 非 `>=`）| ✅ PASSED |
| T5-6 | `test_just_over_fallback_threshold` | fallback_rate=0.41 | `True` | ✅ PASSED |

### Bug 发现 — T5-5: 测试本身掩盖了边界逻辑
- **原测试**: `_make_skill(selections=10, applied=6, fallbacks=4)` 未指定 `completions`，`completions` 默认为 0
- **副作用**: `completion_rate = 0/6 = 0.0 < 0.35` → 触发 completion 进化，`should=True`，与 fallback boundary 测试目的矛盾
- **修复**: 测试改为 `_make_skill(selections=10, applied=6, completions=6, fallbacks=4)` — completion_rate=1.0，确保只测 fallback 边界

---

## 阈值配置（来自 `app/core/config.py`）

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `AUTOEVO_MIN_SELECTIONS` | 5 | 不足此数据量时不触发进化 |
| `AUTOEVO_FALLBACK_RATE` | 0.40 | `total_fallbacks / total_selections > 0.40` 触发 |
| `AUTOEVO_COMPLETION_RATE` | 0.35 | `total_completions / total_applied < 0.35` 触发 |
