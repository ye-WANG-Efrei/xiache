# T2 — evaluator 单元测试报告

**测试文件**: `backend/tests/unit/test_evaluator.py`  
**被测模块**: `app/services/evaluator.py`  
**运行日期**: 2026-04-09  
**结果**: 21/21 通过 ✅

---

## 测试单元

| 测试 ID | 测试名称 | 测试内容 | 预期结果 | 实际结果 |
|---------|----------|----------|----------|----------|
| T2-1 | `test_perfect_captured_skill` | 完美 captured skill，所有字段合法 | `passed=True`, `quality_score=1.0`, 所有 checks 通过 | ✅ PASSED |
| T2-2 | `test_empty_name_fails` | name 为空字符串 | `passed=False`, `has_name=False`, `metadata_complete=False` | ✅ PASSED |
| T2-3 | `test_short_name_fails` | name 只有 2 个字符（低于最小 3 字符）| `passed=False`, `has_name=False` | ✅ PASSED |
| T2-4 | `test_name_with_slash_fails` | name 含路径分隔符 `/` | `passed=False`, `has_name=False` | ✅ PASSED |
| T2-5 | `test_invalid_version_string` | version 为 `"v1"`（不符合 semver）| `version_valid=False`, `passed=False` | ✅ PASSED |
| T2-6 | `test_semver_prerelease_valid` | version 为 `"1.0.3-beta.1"` | `version_valid=True` | ✅ PASSED |
| T2-7 | `test_semver_with_build_metadata` | version 为 `"1.0.0+build.20240101"` | `version_valid=True` | ✅ PASSED |
| T2-8 | `test_version_zero_zero_zero` | version 为 `"0.0.0"` | `version_valid=True` | ✅ PASSED |
| T2-9 | `test_parent_not_in_db` | origin=fixed，parent_skill_id 在 DB 中不存在 | `parent_exists=False`, `passed=False` | ✅ PASSED |
| T2-10 | `test_captured_no_parent_ok` | origin=captured，无 parent_skill_id，caller 传 `parent_exists=True` | `parent_exists=True`, `lineage_valid=True` | ✅ PASSED |
| T2-11 | `test_duplicate_hard_blocks` | 内容指纹已存在（`is_duplicate=True`）| `not_duplicate=False`, `passed=False` | ✅ PASSED |
| T2-12 | `test_duplicate_score_still_high_but_blocked` | 重复内容，其余 10 项全通过 | `quality_score≥0.9`，但 `passed=False`（硬阻断）| ✅ PASSED |
| T2-13 | `test_dangerous_uppercase_blocked` | body 含 `DROP TABLE`（大写）| `no_dangerous_patterns=False`, `passed=False` | ✅ PASSED |
| T2-14 | `test_dangerous_lowercase_blocked` | body 含 `drop table`（小写）| `no_dangerous_patterns=False`, `passed=False` | ✅ PASSED |
| T2-15 | `test_dangerous_shell_injection` | body 含 `curl \| sh` | `no_dangerous_patterns=False`, `passed=False` | ✅ PASSED |
| T2-16 | `test_dangerous_os_system` | body 含 `os.system(...)` | `no_dangerous_patterns=False`, `passed=False` | ✅ PASSED |
| T2-17 | `test_inaccessible_artifact_hard_blocks` | artifact 无法从存储读取 | `artifact_accessible=False`, `passed=False` | ✅ PASSED |
| T2-18 | `test_captured_no_change_summary_ok` | captured origin，无 change_summary | `lineage_valid=True`, `change_explained=True` | ✅ PASSED |
| T2-19 | `test_fixed_short_change_summary_fails` | fixed origin，change_summary 少于 10 字符 | `change_explained=False` | ✅ PASSED |
| T2-20 | `test_fixed_no_parent_declared_fails` | fixed origin，parent_skill_id=None | `lineage_valid=False` | ✅ PASSED |
| T2-21 | `test_fixed_all_good` | fixed origin，parent 存在，change_summary 充分 | `passed=True`, `quality_score=1.0` | ✅ PASSED |

---

## 11-Check 评估体系

| Check | 类型 | 失败时行为 |
|-------|------|-----------|
| `metadata_complete` | soft | 降分 |
| `has_name` | **hard blocker** | 直接 rejected |
| `has_description` | soft | 降分 |
| `version_valid` | **hard blocker** | 直接 rejected |
| `has_body` | soft | 降分 |
| `parent_exists` | **hard blocker** | 直接 rejected |
| `lineage_valid` | soft | 降分 |
| `change_explained` | soft | 降分 |
| `not_duplicate` | **hard blocker** | 直接 rejected |
| `artifact_accessible` | **hard blocker** | 直接 rejected |
| `no_dangerous_patterns` | **hard blocker** | 直接 rejected |

**评分规则**: `quality_score = passed_checks / 11`

**通过条件**: `quality_score >= 0.5` AND 所有 hard blocker 均通过

**状态映射**:
- `accepted`: quality_score ≥ 0.6，所有 hard blocker 通过
- `pending`: 0.3 ≤ quality_score < 0.6，所有 hard blocker 通过
- `rejected`: hard blocker 失败，或 quality_score < 0.3

---

## 发现的 Bug 及修复

### Bug — T2-5 & T2-9: version_valid 和 parent_exists 未作为 hard blocker
- **原代码**: 仅 `has_name`、`no_dangerous_patterns`、`artifact_accessible`、`is_duplicate` 为硬阻断
- **问题**: `version="v1"` 时 10/11 checks 通过，score=0.909 ≥ 0.5，`passed=True`（错误）
- **问题**: `parent_exists=False`（fixed origin）时同理 `passed=True`（错误）
- **修复**: 将 `not checks["version_valid"]` 和 `not parent_exists` 加入 hard_fail 判断
- **理由**: 非法 semver 版本无法进行版本管理；fixed/derived skill 缺少 parent 破坏血缘一致性
