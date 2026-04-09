# Sprint 1 — Skill 存储 & 进化验证报告

> 基于代码静态验证 + 完整端到端测试流程。
> 对应 commit: `c274183`

---

## 1. 架构速览

```
POST /artifacts/stage   →  ZIP 写磁盘 + Artifact 行写 DB
POST /records           →  解析 SKILL.md + 写 skill_records
POST /evolutions        →  评估 11 项检查 → auto-accept / pending / rejected
POST /ingest/openspace  →  更新质量计数 → 阈值触发 auto_evolver → 新 evolution
```

---

## 2. 启动服务

```bash
# 克隆仓库后在项目根目录执行
docker compose up -d

# 验证健康
curl http://localhost:8000/health
# 期望: {"status":"ok","version":"0.1.0"}

# API 文档（交互式）
open http://localhost:8000/docs
```

Dev 模式默认开启，所有请求使用固定 API Key：
```
Authorization: Bearer dev-key-for-testing
```

---

## 3. Skill 怎么存

### 3.1 存储位置

| 数据 | 位置 |
|------|------|
| ZIP artifact 文件 | Docker volume `xiache_artifact_data` → `/data/artifacts/{xx}/{uuid}.zip`（按 UUID 前 2 位分片） |
| skill_records 行 | PostgreSQL `xiache` 数据库，`skill_records` 表 |
| artifact 元数据 | `artifacts` 表 |
| 血缘关系 | `skill_lineage` 表 |
| 进化提案 | `skill_evolutions` 表 |
| 执行记录 | `execution_runs` 表 |

### 3.2 SKILL.md 格式

```markdown
---
name: Blink LED
description: blink led once when triggered by a GPIO signal
version: 1.0.0
tags:
  - iot
  - demo
input_schema:
  type: object
  properties:
    pin:
      type: integer
      description: GPIO pin number (0-39)
output_schema:
  type: object
  properties:
    status:
      type: string
---

## Blink LED Skill

When triggered, sets the specified GPIO pin HIGH for 500ms then LOW.

### Steps
1. Validate pin number is in range 0-39
2. Set pin HIGH
3. Wait 500ms
4. Set pin LOW
5. Return {status: "ok"}
```

### 3.3 存 Skill 的两步流程

**Step 1 — Stage artifact（上传 SKILL.md）**

```bash
# 先把 SKILL.md 内容写到文件
cat > /tmp/SKILL.md << 'EOF'
---
name: Blink LED
description: blink led once when triggered by a GPIO signal
version: 1.0.0
tags:
  - iot
  - demo
input_schema:
  type: object
  properties:
    pin: {type: integer, description: GPIO pin number}
output_schema:
  type: object
  properties:
    status: {type: string}
---

## Blink LED Skill

When triggered, sets the specified GPIO pin HIGH for 500ms then LOW.

### Steps
1. Validate pin number is in range 0-39
2. Set pin HIGH
3. Wait 500ms
4. Set pin LOW
5. Return {status: "ok"}
EOF

curl -s -X POST http://localhost:8000/api/v1/artifacts/stage \
  -H "Authorization: Bearer dev-key-for-testing" \
  -F "files=@/tmp/SKILL.md" | jq .
```

**期望返回：**
```json
{
  "artifact_id": "3f2a1b4c-...",
  "stats": {
    "file_count": 1,
    "total_size": 412
  }
}
```

此时 ZIP 已写入：`/data/artifacts/3f/3f2a1b4c-....zip`

---

**Step 2 — 创建 skill record**

```bash
# 用上面返回的 artifact_id
ARTIFACT_ID="3f2a1b4c-..."

curl -s -X POST http://localhost:8000/api/v1/records \
  -H "Authorization: Bearer dev-key-for-testing" \
  -H "Content-Type: application/json" \
  -d "{
    \"record_id\": \"blink_led_v1\",
    \"artifact_id\": \"$ARTIFACT_ID\",
    \"origin\": \"captured\"
  }" | jq .
```

**期望返回：**
```json
{
  "record_id": "blink_led_v1",
  "artifact_id": "3f2a1b4c-...",
  "artifact_ref": "artifact://blink_led_v1",
  "name": "Blink LED",
  "description": "blink led once when triggered by a GPIO signal",
  "version": "1.0.0",
  "origin": "captured",
  "visibility": "public",
  "level": "tool_guide",
  "tags": ["iot", "demo"],
  "input_schema": {"type": "object", "properties": {"pin": {...}}},
  "output_schema": {"type": "object", "properties": {"status": {...}}},
  "created_by": "dev",
  "content_fingerprint": "a3b4c5...",
  "parent_skill_ids": [],
  "created_at": "2026-04-09T..."
}
```

**验证存入 DB：**
```bash
# 查询（需要 psql 或进入容器）
docker exec -it xiache-postgres psql -U xiache -d xiache \
  -c "SELECT id, name, version, tags, total_selections FROM skill_records WHERE id='blink_led_v1';"
```

**查询 artifact 文件是否存在：**
```bash
docker exec xiache-backend ls /data/artifacts/3f/
# 应看到: 3f2a1b4c-....zip
```

---

## 4. Skill 怎么进化

### 4.1 进化流程

```
Stage 新 artifact（v2 的 SKILL.md）
    ↓
POST /evolutions  {parent_skill_id, candidate_skill_id, origin="fixed", change_summary}
    ↓
11 项检查（evaluator）
    ↓
score ≥ 0.6 → auto-accept → 新 SkillRecord(id=candidate_skill_id) + lineage 边
score 0.3-0.6 → pending → 人工 POST /evolutions/{id}/accept
score < 0.3   → rejected
```

### 4.2 11 项评估检查

| # | 检查 | 说明 | 硬拦截 |
|---|---|---|---|
| 1 | `metadata_complete` | name + description + version + ≥1 tag 都有 | |
| 2 | `has_name` | ≥3 字符，无路径符 | |
| 3 | `has_description` | ≥10 字符 | |
| 4 | `version_valid` | 合法 semver (x.y.z) | |
| 5 | `has_body` | SKILL.md body ≥20 字符 | |
| 6 | `parent_exists` | parent_skill_id 在 DB 查得到 | |
| 7 | `lineage_valid` | fixed/derived 必须声明 parent | |
| 8 | `change_explained` | fixed/derived 的 change_summary ≥10 字符 | |
| 9 | `not_duplicate` | 内容指纹不重复 | ✅ |
| 10 | `artifact_accessible` | ZIP 能从 storage 读出 | ✅ |
| 11 | `no_dangerous_patterns` | 无危险代码（大小写不敏感） | ✅ |

**auto-accept 阈值：`score ≥ 0.6`（config: `AUTO_ACCEPT_THRESHOLD`）**

### 4.3 提交进化（v2 加 delay 参数）

**Step 1 — Stage v2 artifact**

```bash
cat > /tmp/SKILL_v2.md << 'EOF'
---
name: Blink LED
description: blink led with configurable delay when triggered by a GPIO signal
version: 1.0.1
tags:
  - iot
  - demo
input_schema:
  type: object
  properties:
    pin: {type: integer, description: GPIO pin number}
    delay_ms: {type: integer, description: Blink duration ms, default: 500}
output_schema:
  type: object
  properties:
    status: {type: string}
---

## Blink LED Skill v1.0.1

When triggered, sets the specified GPIO pin HIGH for `delay_ms` milliseconds then LOW.

### Steps
1. Validate pin number is in range 0-39
2. Read delay_ms from input (default 500)
3. Set pin HIGH
4. Wait delay_ms milliseconds
5. Set pin LOW
6. Return {status: "ok"}
EOF

curl -s -X POST http://localhost:8000/api/v1/artifacts/stage \
  -H "Authorization: Bearer dev-key-for-testing" \
  -F "files=@/tmp/SKILL_v2.md" | jq .
# 记录返回的 artifact_id → V2_ARTIFACT_ID
```

**Step 2 — 提交 evolution**

```bash
V2_ARTIFACT_ID="<上一步返回的 artifact_id>"

curl -s -X POST http://localhost:8000/api/v1/evolutions \
  -H "Authorization: Bearer dev-key-for-testing" \
  -H "Content-Type: application/json" \
  -d "{
    \"artifact_id\": \"$V2_ARTIFACT_ID\",
    \"parent_skill_id\": \"blink_led_v1\",
    \"candidate_skill_id\": \"blink_led_v2\",
    \"origin\": \"fixed\",
    \"change_summary\": \"add configurable delay_ms parameter\"
  }" | jq .
```

**期望返回（auto-accepted，score=1.0）：**
```json
{
  "evolution_id": "9a8b7c...",
  "status": "accepted",
  "proposed_name": "Blink LED",
  "parent_skill_id": "blink_led_v1",
  "candidate_skill_id": "blink_led_v2",
  "result_record_id": "blink_led_v2",
  "auto_accepted": true,
  "evaluation": {
    "passed": true,
    "quality_score": 1.0,
    "notes": "All checks passed.",
    "checks": {
      "metadata_complete": true,
      "has_name": true,
      "has_description": true,
      "version_valid": true,
      "has_body": true,
      "parent_exists": true,
      "lineage_valid": true,
      "change_explained": true,
      "not_duplicate": true,
      "artifact_accessible": true,
      "no_dangerous_patterns": true
    }
  }
}
```

**验证新版本已存在：**
```bash
curl -s http://localhost:8000/api/v1/records/blink_led_v2 \
  -H "Authorization: Bearer dev-key-for-testing" | jq '{record_id, version, artifact_ref}'
# {"record_id":"blink_led_v2","version":"1.0.1","artifact_ref":"artifact://blink_led_v2"}
```

**验证血缘关系：**
```bash
docker exec -it xiache-postgres psql -U xiache -d xiache \
  -c "SELECT child_id, parent_id FROM skill_lineage WHERE child_id='blink_led_v2';"
# child_id     | parent_id
# blink_led_v2 | blink_led_v1
```

---

## 5. 自演化（从执行数据学习）

当 OpenSpace agent 执行失败率过高时，系统自动提 evolution。

### 5.1 触发条件（config 可调）

| 参数 | 默认值 | 说明 |
|---|---|---|
| `AUTOEVO_MIN_SELECTIONS` | 5 | 至少采样 5 次才评估 |
| `AUTOEVO_FALLBACK_RATE` | 0.40 | fallback_rate > 40% 触发 |
| `AUTOEVO_COMPLETION_RATE` | 0.35 | completion_rate < 35% 触发 |

### 5.2 模拟触发

```bash
# 连续 POST 5 次执行失败（skill_applied=false, task_completed=false）
for i in 1 2 3 4 5; do
curl -s -X POST http://localhost:8000/api/v1/ingest/openspace \
  -H "Authorization: Bearer dev-key-for-testing" \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"task-$i\",
    \"timestamp\": \"2026-04-09T10:0$i:00Z\",
    \"task_completed\": false,
    \"execution_note\": \"agent could not follow step 3, fell back to manual\",
    \"skill_judgments\": [{
      \"skill_id\": \"blink_led_v2\",
      \"skill_applied\": false,
      \"note\": \"step 3 instructions unclear\"
    }],
    \"analyzed_by\": \"claude-3-opus\",
    \"analyzed_at\": \"2026-04-09T10:0$i:01Z\"
  }" | jq '{task_id, counters_updated, evolutions_triggered}'; done
```

**第 5 次返回：**
```json
{
  "task_id": "task-5",
  "counters_updated": ["blink_led_v2"],
  "evolutions_triggered": ["blink_led_v2"]
}
```

**`evolutions_triggered` 非空**表示 auto_evolver 已启动，LLM 重写了 SKILL.md 并提交了新 evolution（需配置 `LLM_API_KEY`）。

### 5.3 验证自动生成的 evolution

```bash
curl -s "http://localhost:8000/api/v1/evolutions?status=pending" \
  -H "Authorization: Bearer dev-key-for-testing" | jq '.items[] | {evolution_id, parent_skill_id, candidate_skill_id, auto_accepted}'
```

---

## 6. 数据流完整图

```
SKILL.md 文件
    │
    ▼ POST /artifacts/stage
ZIP 打包 → SHA-256 fingerprint
    │
    ├── 磁盘: /data/artifacts/{xx}/{uuid}.zip
    └── DB: artifacts 表 (id, fingerprint, file_names)
    │
    ▼ POST /records
parse_skill_md() 提取 name/description/version/tags/input_schema/output_schema
generate_embedding() → vector(1536)
    │
    └── DB: skill_records 表 (id=record_id, embedding, version, input_schema ...)
    │
    ▼ POST /evolutions  (进化)
Stage 新 artifact → evaluate_evolution() 11 项检查
    │
    ├── score ≥ 0.6 → accepted → 新 skill_records 行 + skill_lineage 边
    ├── 0.3-0.6    → pending  → 等人工 /accept
    └── < 0.3      → rejected
    │
    ▼ POST /ingest/openspace  (执行反馈)
更新 skill_records.total_selections/applied/completions/fallbacks
    │
    └── 阈值触发 → auto_evolver:
            load SKILL.md → LLM rewrite → 新 ZIP → Stage → POST evolution
```

---

## 7. 常见报错排查

| 报错 | 原因 | 解法 |
|---|---|---|
| `404 Artifact not found` | record 引用的 artifact_id 不存在 | 先 stage artifact，再创建 record |
| `409 fingerprint_record_id_conflict` | 同内容已注册为其他 record_id | 内容重复，修改 SKILL.md 或用已有 record_id |
| `409 candidate_skill_id already exists` | 目标 record_id 已有 skill | 换一个 candidate_skill_id |
| `evolution rejected, score < 0.3` | SKILL.md 缺 name/description/body | 补齐必填字段 |
| `evolutions_triggered` 始终空 | `LLM_API_KEY` 未配置 | 在 `.env` 设置 `LLM_API_KEY` |
| `evolutions_triggered` 空但阈值已达 | 已有 pending evolution 在等待 | 先 accept/reject 现有 pending |

---

## 8. Migration 顺序（全新数据库）

```bash
# docker-compose 自动执行 01_init.sql（包含所有表）
# 如已有旧库，按顺序手动执行：
psql -U xiache -d xiache -f backend/migrations/add_evolutions.sql
psql -U xiache -d xiache -f backend/migrations/add_execution_runs.sql
psql -U xiache -d xiache -f backend/migrations/add_skill_structured_fields.sql
psql -U xiache -d xiache -f backend/migrations/add_evolution_candidate_id.sql
psql -U xiache -d xiache -f backend/migrations/add_quality_counters.sql
```

---

*Sprint 1 覆盖：Skill 结构化存储 · 11 项 Evaluator · Evolution 血缘机制 · OpenSpace 执行数据 ingest · LLM 驱动自演化*
