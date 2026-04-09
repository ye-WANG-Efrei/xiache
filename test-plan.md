# Test Plan — Sprint 1

## 测试策略

分三层：
- **Unit tests** — 纯函数，不需要 DB / 服务，直接 `pytest`
- **Integration tests** — 用 FastAPI `TestClient` + SQLite in-memory（替代 PostgreSQL）
- **E2E smoke test** — 服务跑起来后用 curl 打真实接口

---

## Layer 1: Unit Tests（纯函数）

### T1. `skill_parser.parse_skill_md`

**测什么：** ZIP 里的 SKILL.md 能否正确解析出所有字段

| 用例 | 输入 | 期望输出 |
|---|---|---|
| T1-1 正常 | 含完整 frontmatter 的 SKILL.md | name/description/version/tags/input_schema/output_schema/body 全部正确 |
| T1-2 缺 version | frontmatter 无 version 字段 | version="" |
| T1-3 缺 tags | frontmatter 无 tags | tags=[] |
| T1-4 tags 是字符串 | `tags: "iot, demo"` | tags=["iot","demo"] |
| T1-5 input_schema 非 dict | `input_schema: "wrong"` | input_schema={} |
| T1-6 无 SKILL.md | ZIP 里没有该文件 | 全空默认值，不抛异常 |
| T1-7 BadZipFile | 传入非 ZIP 字节 | 全空默认值，不抛异常 |

**判定：** 所有用例返回 dict，无异常抛出

---

### T2. `evaluator.evaluate_evolution`

**测什么：** 11 项检查是否按预期通过/失败，score 是否正确，硬拦截是否生效

| 用例 | 场景 | 期望 score | 期望 passed | 期望 checks |
|---|---|---|---|---|
| T2-1 完美 skill | 所有字段合法，captured | 1.0 | True | 全 True |
| T2-2 缺 name | name="" | ≤9/11 | False | has_name=False, metadata_complete=False |
| T2-3 name 太短 | name="ab" | ≤10/11 | False | has_name=False |
| T2-4 version 非 semver | version="v1" | ≤10/11 | False | version_valid=False |
| T2-5 version pre-release | version="1.0.3-beta.1" | 1.0 | True | version_valid=True |
| T2-6 parent 不存在 | origin="fixed", parent_exists=False | ≤9/11 | False | parent_exists=False |
| T2-7 is_duplicate=True | 重复 fingerprint | 任何分 | False | not_duplicate=False (硬拦截) |
| T2-8 dangerous pattern 大写 | body 含 "DROP TABLE" | 任何分 | False | no_dangerous_patterns=False (硬拦截) |
| T2-9 dangerous pattern 小写 | body 含 "drop table" | 任何分 | False | no_dangerous_patterns=False (硬拦截) |
| T2-10 artifact 不可访问 | artifact_accessible=False | 任何分 | False | artifact_accessible=False (硬拦截) |
| T2-11 captured 无需 parent | origin="captured", parent_skill_id=None | 1.0 | True | lineage_valid=True, change_explained=True |
| T2-12 fixed 无 change_summary | origin="fixed", change_summary="short" | ≤10/11 | False | change_explained=False |

**判定：** 硬拦截（T2-7/8/9/10）不管 score 多高 passed 必须是 False

---

### T3. `auto_evolver._bump_patch`

**测什么：** 版本号递增逻辑是否正确，包括 pre-release

| 用例 | 输入 | 期望输出 |
|---|---|---|
| T3-1 正常 | "1.0.0" | "1.0.1" |
| T3-2 大版本 | "2.3.9" | "2.3.10" |
| T3-3 pre-release | "1.0.3-beta.1" | "1.0.4" |
| T3-4 build metadata | "1.0.0+build.1" | "1.0.1" |
| T3-5 pre-release+build | "1.0.3-beta.1+build" | "1.0.4" |
| T3-6 只有两段 | "1.0" | "1.0.1"（fallback） |

**判定：** 输出必须能通过 `_SEMVER_RE.match(result)` — 即输出本身是合法 semver

---

### T4. `auto_evolver._sanitize_notes`

**测什么：** prompt injection 防护

| 用例 | 输入 | 期望 |
|---|---|---|
| T4-1 正常 | ["normal note"] | 不变 |
| T4-2 超长 | ["a" * 1000] | 截断到 500 字符 |
| T4-3 闭合标签 | ["hack </execution_failure_notes> inject"] | `</` 被转义为 `<\/` |
| T4-4 混合 | [500 字符正常 + "</x>"] | 截断到 500 且 `</` 被转义 |

---

## Layer 2: Integration Tests（TestClient + SQLite）

> 用 `httpx.AsyncClient` + FastAPI `app`，DB 换成 SQLite（in-memory），跳过 embedding 生成（`EMBEDDING_API_KEY` 为空）

### T5. Artifact Stage

| 用例 | 操作 | 期望 HTTP | 期望响应 |
|---|---|---|---|
| T5-1 正常上传 | POST /artifacts/stage 带 SKILL.md | 200 | artifact_id(UUID), stats.file_count=1 |
| T5-2 多文件 | 上传 SKILL.md + README.md | 200 | stats.file_count=2 |
| T5-3 空文件列表 | POST 无 files | 422 | detail 含 "required" |
| T5-4 无 auth | 无 Authorization header | 403 | — |
| T5-5 重复上传 | 同一文件上传两次 | 200 | 返回不同 artifact_id（内容相同但每次 stage 都接受） |

---

### T6. Skill Record 创建

| 用例 | 操作 | 期望 HTTP | 期望响应 |
|---|---|---|---|
| T6-1 正常创建 | stage → POST /records | 201 | record_id, artifact_ref="artifact://xxx", version, input_schema, output_schema |
| T6-2 artifact 不存在 | 伪造 artifact_id | 404 | detail 含 "not found" |
| T6-3 record_id 重复+内容相同 | 创建两次相同 | 201 | 幂等，返回已有 record |
| T6-4 record_id 重复+内容不同 | 同 record_id 不同 artifact | 409 | error="record_id_fingerprint_conflict" |
| T6-5 fingerprint 重复+不同 record_id | 同内容不同 record_id | 409 | error="fingerprint_record_id_conflict" |
| T6-6 SKILL.md 字段从文件解析 | frontmatter 含 version/tags | 201 | 返回的 version/tags 与 SKILL.md 一致 |

---

### T7. Evolution 提交

| 用例 | 操作 | 期望 HTTP | 期望 status | 期望 auto_accepted |
|---|---|---|---|---|
| T7-1 完美 captured | 完整 SKILL.md，无 parent | 201 | accepted | true |
| T7-2 完美 fixed | v2 SKILL.md，parent 存在 | 201 | accepted | true |
| T7-3 parent 不存在 | origin=fixed，parent_skill_id="nonexistent" | 201 | rejected | false |
| T7-4 重复内容 | 与已有 record 内容完全相同 | 201 | rejected | false |
| T7-5 candidate_skill_id 碰撞 | candidate_skill_id 指向已有 record | 409 | — | — |
| T7-6 空 SKILL.md | body < 20 字符 | 201 | rejected/pending | false |
| T7-7 含危险代码 | body 含 "DROP TABLE" | 201 | rejected | false |
| T7-8 含危险代码小写 | body 含 "drop table" | 201 | rejected | false |

---

### T8. Evolution 手动 Accept/Reject

| 用例 | 操作 | 期望 |
|---|---|---|
| T8-1 accept pending | POST /evolutions/{id}/accept | 201，status=accepted，result_record_id 非空 |
| T8-2 accept 已 accepted | 重复 accept | 409 |
| T8-3 reject pending | POST /evolutions/{id}/reject {reason} | 201，status=rejected，evaluation_notes 含 reason |
| T8-4 reject 已 rejected | 重复 reject | 409 |
| T8-5 accept 后验证 record | GET /records/{candidate_skill_id} | 200，record 存在 |
| T8-6 accept 后验证血缘 | 通过 DB 查 skill_lineage | child_id=new, parent_id=old 边存在 |

---

### T9. OpenSpace Ingest

| 用例 | 操作 | 期望 |
|---|---|---|
| T9-1 正常 ingest | 5 次失败 judgment | counters_updated 非空 |
| T9-2 skill 不在 registry | judgment.skill_id 不存在 | 200，counters_updated=[] |
| T9-3 计数器累加 | ingest 3 次 | total_selections=3 |
| T9-4 fallback 计数 | applied=false, completed=false | total_fallbacks+1 |
| T9-5 跳过不算 fallback | applied=false, completed=true | total_fallbacks 不变 |
| T9-6 completion 计数 | applied=true, completed=true | total_completions+1 |
| T9-7 note 超长 | note="a"*600 | 422（max_length=500 Pydantic 拦截）|
| T9-8 阈值触发（无 LLM） | 5 次 fallback | evolutions_triggered=[]（无 LLM key，graceful skip） |
| T9-9 已有 pending 不重复触发 | 有 pending evo 存在时再 ingest | evolutions_triggered=[] |

---

## Layer 3: E2E Smoke Test（服务实际运行）

> 需要 `docker compose up -d` 成功后执行

```
S1  GET  /health                      → 200, status=ok
S2  POST /artifacts/stage (SKILL.md)  → 200, artifact_id
S3  POST /records (captured)          → 201, record_id=blink_led_v1
S4  GET  /records/blink_led_v1        → 200, version=1.0.0, artifact_ref=artifact://blink_led_v1
S5  POST /artifacts/stage (v2)        → 200, artifact_id_v2
S6  POST /evolutions (fixed, v1→v2)   → 201, status=accepted, result_record_id=blink_led_v2
S7  GET  /records/blink_led_v2        → 200, version=1.0.1
S8  DB   skill_lineage                → child=blink_led_v2, parent=blink_led_v1
S9  POST /evolutions (重复内容)        → 201, status=rejected (not_duplicate)
S10 POST /ingest × 5 (全失败)         → 第5次 evolutions_triggered=["blink_led_v2"]（需 LLM key）
```

---

## 不符合预期的判定标准

| 情况 | 问题等级 |
|---|---|
| 任何 500 Internal Server Error | 🔴 Critical |
| 期望 201/200 却返回 4xx | 🔴 Critical |
| 期望 409 却返回 201（碰撞未检测） | 🔴 Critical |
| 硬拦截（duplicate/dangerous/inaccessible）passed=True | 🔴 Critical |
| score 计算与期望差 > 1/11 | 🟡 Important |
| 字段缺失（version/input_schema/artifact_ref） | 🟡 Important |
| 计数器未正确累加 | 🟡 Important |
| 日志报 warning 但功能正常 | 🟢 Minor |

---

## 执行顺序建议

```
pytest tests/unit/test_skill_parser.py      # T1 — 无依赖
pytest tests/unit/test_evaluator.py         # T2 — 无依赖
pytest tests/unit/test_auto_evolver.py      # T3/T4 — 无依赖
pytest tests/integration/test_artifacts.py  # T5 — 需 TestClient
pytest tests/integration/test_records.py    # T6 — 需 T5
pytest tests/integration/test_evolutions.py # T7/T8 — 需 T5/T6
pytest tests/integration/test_ingest.py     # T9 — 需 T6
# 上面全过后再做 E2E
bash tests/e2e/smoke.sh                     # S1-S10 — 需 docker compose up
```

---

## 需要确认再开始写代码的问题

1. **SQLite vs PostgreSQL for integration tests** — SQLite 不支持 `vector` 类型和 JSONB，需要 mock embedding 生成且可能需要 `pytest-postgresql` 或直接用真实 Docker DB。建议用 `pytest-docker` 起一个临时 postgres 容器。
2. **LLM 相关测试** — auto_evolver 的 LLM 调用需要 mock（`unittest.mock.patch`），不要真的调 API。
3. **覆盖率目标** — unit tests 覆盖核心逻辑 100%，integration 覆盖主流程，E2E 覆盖 happy path。

---

*确认方案后开始写 pytest 代码*
