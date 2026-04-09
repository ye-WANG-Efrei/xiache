# Xiache — Agent-Native Skill Registry Platform

> **一句话定义**：Xiache 是一个面向 AI Agent 的技能注册平台，类比 GitHub 之于代码——Agent 可以发现、发布、演化、执行技能，平台自动追踪版本血缘、评估质量、管理执行记录。

---

## 目录

1. [项目背景与设计理念](#1-项目背景与设计理念)
2. [系统整体架构](#2-系统整体架构)
3. [目录结构](#3-目录结构)
4. [技术栈](#4-技术栈)
5. [数据库设计](#5-数据库设计)
6. [后端 API 详解](#6-后端-api-详解)
7. [后端服务层详解](#7-后端服务层详解)
8. [MCP Server 详解](#8-mcp-server-详解)
9. [前端详解](#9-前端详解)
10. [环境变量与配置](#10-环境变量与配置)
11. [核心业务逻辑](#11-核心业务逻辑)
12. [部署指南](#12-部署指南)
13. [开发指南](#13-开发指南)
14. [扩展路线图](#14-扩展路线图)

---

## 1. 项目背景与设计理念

### 为什么需要 Xiache？

MCP（Model Context Protocol）解决了 Agent 调用工具的协议问题，但存在关键缺失：
- 技能没有版本管理，无法追溯历史
- 技能之间没有血缘关系，无法知道"这个技能从哪个技能演化来的"
- 没有质量评估机制，坏技能和好技能无法区分
- 没有执行记录，无法审计 Agent 做了什么

**Xiache 的核心思路**：把 GitHub 的 PR/Review/Merge 工作流搬到技能管理上：
- `commit` → 技能变更
- `pull request` → 技能演化提案（Evolution）
- `code review` → 质量评估（Evaluator）
- `merge` → 版本发布（accepted SkillRecord）
- `git log` → 技能血缘图（Lineage）

### 三层执行模型

```
┌─────────────────────────┐
│   Reasoning Layer       │  AI Agent 思考、规划、选择技能
├─────────────────────────┤
│   Digital Layer         │  代码执行、API 调用、数据处理
├─────────────────────────┤
│   Physical Layer        │  硬件控制、嵌入式设备、IoT 指令
└─────────────────────────┘
```

每个 ExecutionRun 记录属于哪一层，target_env 字段记录硬件环境（board_type, interface, architecture）。

---

## 2. 系统整体架构

```
┌──────────────────────────────────────────────────────────┐
│                   AI Agent (Claude / 其他)                │
│                                                          │
│  使用 MCP Tools: search_skills / execute_task / publish  │
└────────────────────┬─────────────────────────────────────┘
                     │ stdio (MCP 协议)
                     ▼
┌──────────────────────────────────────────────────────────┐
│                   mcp_server.py                          │
│   7 个 MCP Tool → HTTP 调用后端 API + Bearer Token        │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP /api/v1
                     ▼
┌──────────────────────────────────────────────────────────┐
│                FastAPI 后端 (Python 3.12)                 │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐  │
│  │artifacts │ │ records  │ │ evolutions │ │  runs    │  │
│  └──────────┘ └──────────┘ └────────────┘ └──────────┘  │
│  ┌──────────┐                                            │
│  │  search  │                                            │
│  └──────────┘                                            │
│                                                          │
│  Services: skill_parser / embedding / search / evaluator │
└────┬───────────────────────────────────────┬─────────────┘
     │ SQLAlchemy asyncpg                    │ aiofiles
     ▼                                       ▼
┌─────────────────┐                ┌─────────────────────┐
│  PostgreSQL 16  │                │  本地文件系统        │
│  + pgvector     │                │  data/artifacts/    │
│                 │                │  {2char}/{uuid}.zip │
│  Tables:        │                └─────────────────────┘
│  api_keys       │
│  artifacts      │                ┌─────────────────────┐
│  skill_records  │                │  OpenAI 兼容 API    │
│  skill_lineage  │◄───────────────│  (可选,生成 embedding)│
│  skill_evols    │                └─────────────────────┘
│  execution_runs │
└─────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  Next.js 前端 (React 18)                  │
│                                                          │
│  首页: 技能列表 + 搜索过滤                                 │
│  详情页: Overview / Lineage Graph / Diff Viewer          │
│                                                          │
│  通过 axios 调用后端 REST API                             │
└──────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
xiache/
├── README.md                        # 本文件
├── Systemarchitect.md               # GitHub 交互模型设计文档
├── architectbyOpenspace.md          # 完整平台架构设计（中文）
├── docker-compose.yml               # 3 服务编排（postgres + backend + frontend）
├── .env.example                     # 环境变量模板（根目录）
│
├── backend/
│   ├── Dockerfile                   # Python 3.12 多阶段构建
│   ├── requirements.txt             # Python 依赖
│   ├── .env.example                 # 后端环境变量模板
│   ├── mcp_server.py                # MCP stdio 服务器（供 Agent 使用）
│   ├── migrations/
│   │   └── init.sql                 # 数据库初始化 SQL
│   └── app/
│       ├── main.py                  # FastAPI 应用入口，CORS，路由注册
│       ├── core/
│       │   ├── config.py            # Settings（pydantic-settings，读取 .env）
│       │   ├── database.py          # SQLAlchemy async engine + session
│       │   └── storage.py           # Artifact ZIP 文件的读写（磁盘）
│       ├── models/
│       │   └── db.py                # SQLAlchemy ORM 模型定义
│       ├── schemas/
│       │   └── api.py               # Pydantic 请求/响应 schema
│       ├── services/
│       │   ├── skill_parser.py      # 从 ZIP 中解析 SKILL.md（YAML frontmatter）
│       │   ├── embedding.py         # 调用 OpenAI 兼容 API 生成 embedding
│       │   ├── search.py            # 纯 Python BM25 + 余弦相似度
│       │   └── evaluator.py         # 技能演化质量评估（6 项检查）
│       └── api/v1/
│           ├── router.py            # 聚合所有路由
│           ├── deps.py              # API Key 鉴权依赖
│           ├── health.py            # GET /health
│           ├── artifacts.py         # POST /artifacts/stage（上传文件）
│           ├── records.py           # CRUD /records
│           ├── search.py            # GET /search（混合搜索）
│           ├── evolutions.py        # /evolutions（PR 工作流）
│           └── runs.py              # /runs（执行记录）
│
└── frontend/
    ├── Dockerfile                   # Node 20 alpine 多阶段构建
    ├── package.json                 # Next.js 14.2 + React 18 + TailwindCSS
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    └── src/
        ├── lib/
        │   └── api.ts               # TypeScript Axios API 客户端
        ├── components/
        │   ├── SearchBar.tsx        # 搜索框组件
        │   ├── SkillCard.tsx        # 技能卡片（列表页使用）
        │   ├── LineageGraph.tsx     # 力导向图（血缘可视化）
        │   └── DiffViewer.tsx       # Unified diff 查看器
        └── app/
            ├── layout.tsx           # 全局 Layout（导航栏 + 页脚）
            ├── page.tsx             # 首页（技能注册表列表）
            └── skills/[id]/
                └── page.tsx         # 技能详情页
```

---

## 4. 技术栈

| 层次 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 后端框架 | FastAPI | 最新 | 异步 Python Web 框架 |
| 异步运行时 | uvicorn | 1 worker | ASGI 服务器 |
| 数据库 ORM | SQLAlchemy | 2.x async | 异步 ORM |
| 数据库驱动 | asyncpg | — | 高性能 PostgreSQL async driver |
| 数据库 | PostgreSQL 16 | + pgvector | 向量搜索扩展 |
| 配置管理 | pydantic-settings | 2.x | .env 读取 + 类型验证 |
| 请求校验 | Pydantic | v2 | 请求/响应 schema |
| 文件 IO | aiofiles | — | 异步文件读写 |
| MCP 协议 | mcp (SDK) | — | stdio 服务器 |
| 前端框架 | Next.js | 14.2 | React Server Components |
| UI 样式 | TailwindCSS | 3.4 | 原子化 CSS |
| HTTP 客户端 | Axios | — | 前端 REST 请求 |
| 图标库 | Lucide React | — | SVG 图标 |
| 图可视化 | react-force-graph-2d | — | 力导向血缘图 |
| 日期格式化 | date-fns | — | 时间格式化 |
| 容器化 | Docker + Compose | — | 3 服务编排 |

---

## 5. 数据库设计

### 初始化

数据库通过 `backend/migrations/init.sql` 初始化，Docker Compose 启动时自动执行。

### 表结构

#### `api_keys` — API 鉴权

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| key_hash | TEXT UNIQUE | SHA256(API Key) |
| name | TEXT | 用途描述 |
| owner | TEXT | 所属方 |
| is_active | BOOL | 是否启用 |
| created_at | TIMESTAMP | 创建时间 |

> **Dev 模式**：`XIACHE_DEV_MODE=true` 时，直接比对 `DEV_API_KEY` 明文字符串，不查库。

#### `artifacts` — 技能包存储元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 也是磁盘文件名 `{id}.zip` |
| file_count | INT | ZIP 内文件数 |
| file_names | JSONB | 文件名列表 |
| content_fingerprint | TEXT | 整个 ZIP 的 SHA256 |
| created_by | TEXT | 上传方 |
| created_at | TIMESTAMP | — |

> 文件存储路径：`{STORAGE_PATH}/{id前2位}/{id}.zip`（分片存储，避免单目录过多文件）

#### `skill_records` — 已发布技能（核心表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 技能唯一 ID（可自定义，如 `org/skill-name/v1`）|
| artifact_id | UUID FK | 关联 artifacts 表 |
| name | TEXT | 显示名称 |
| description | TEXT | 描述 |
| origin | TEXT | 来源类型（captured/fixed/derived/seeded 等）|
| visibility | TEXT | 可见性（public/group_only/private）|
| level | TEXT | 层级（workflow/tool_guide/reference）|
| tags | JSONB | 标签数组 |
| created_by | TEXT | 发布者 |
| change_summary | TEXT | 变更说明（演化时填写）|
| content_diff | TEXT | Unified diff 内容 |
| embedding | VECTOR(1536) | 语义向量（pgvector）|
| content_fingerprint | TEXT | 内容 SHA256（去重用）|
| created_at | TIMESTAMP | — |

#### `skill_lineage` — 技能血缘关系

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| child_id | TEXT FK → skill_records | 子技能 |
| parent_id | TEXT FK → skill_records | 父技能 |
| UNIQUE(child_id, parent_id) | — | 防止重复边 |

> 一个技能可以有多个父技能（从多个技能 derive）

#### `skill_evolutions` — 演化提案（PR 等价物）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| artifact_id | UUID FK | 提案对应的 artifact |
| parent_skill_id | TEXT FK | 基于哪个技能演化（可 NULL，表示全新）|
| origin | TEXT | fixed/derived/captured 等 |
| status | TEXT | **pending/evaluating/accepted/rejected** |
| proposed_name | TEXT | 提案技能名 |
| proposed_desc | TEXT | 提案描述 |
| change_summary | TEXT | 变更摘要 |
| proposed_by | TEXT | 提案者 |
| quality_score | FLOAT | 0.0–1.0 质量分 |
| auto_accepted | BOOL | 是否自动 accept |
| evaluated_at | TIMESTAMP | 评估完成时间 |
| result_record_id | TEXT FK | accept 后创建的 SkillRecord ID |
| created_at | TIMESTAMP | — |

#### `execution_runs` — 执行记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| skill_id | TEXT FK | 使用的技能 |
| task | TEXT | 任务描述 |
| status | TEXT | **running/success/failed** |
| executor_type | TEXT | reasoning/digital/physical |
| target_env | JSONB | 硬件环境 `{board_type, interface, architecture}` |
| started_at | TIMESTAMP | — |
| completed_at | TIMESTAMP | — |
| result | TEXT | 执行结果 |
| error | TEXT | 错误信息 |
| run_log | TEXT | 完整执行日志 |
| called_by | TEXT | 调用方（Agent ID 等）|

### 关系图

```
artifacts ──< skill_records >──< skill_lineage >──< skill_records
                    │
                    └──< skill_evolutions >── (result_record_id) ──> skill_records
                    └──< execution_runs
```

---

## 6. 后端 API 详解

**Base URL**: `/api/v1`
**鉴权**: 所有端点需要 `Authorization: Bearer <api_key>`
**API Docs**: `http://localhost:8000/docs`（Swagger UI）

---

### Health

#### `GET /health`

**响应**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "db_status": "connected"
}
```

---

### Artifacts（技能包上传）

#### `POST /artifacts/stage`

将技能文件上传为 artifact（ZIP 包），获得 `artifact_id` 后才能创建 skill record 或 evolution。

**请求**: `multipart/form-data`，字段名 `files`，支持多文件。

**响应**:
```json
{
  "artifact_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_count": 3,
  "file_names": ["SKILL.md", "skill.yaml", "main.py"],
  "content_fingerprint": "sha256:abc123..."
}
```

**内部逻辑**:
1. 接收 multipart 文件（或已是 ZIP 直接存储，或多文件打包成 ZIP）
2. 计算 SHA256 fingerprint
3. 以 UUID 命名，存储到 `{STORAGE_PATH}/{uuid前2位}/{uuid}.zip`
4. 写入 artifacts 表

---

### Records（技能记录 CRUD）

#### `POST /records`

发布一个技能（从已上传的 artifact 创建 SkillRecord）。

**请求体**:
```json
{
  "record_id": "org/my-skill/v1",
  "artifact_id": "...",
  "origin": "captured",
  "visibility": "public",
  "level": "tool_guide",
  "parent_skill_ids": [],
  "change_summary": "初始版本",
  "content_diff": "--- ...\n+++ ..."
}
```

**响应**: 完整 SkillRecord JSON（含 ID、名称、描述、tags、embedding 等）

**内部逻辑**:
1. 从 artifact ZIP 中解析 SKILL.md（提取 frontmatter 中的 name/description/tags 和 body）
2. 去重检查：① 同 record_id 已存在 → 409；② 同 content_fingerprint 已存在 → 409
3. 生成 embedding（name + description + tags 拼接后调用 embedding API）
4. 写入 skill_records 表
5. 写入 skill_lineage 表（每个 parent_skill_id 创建一条边）

#### `GET /records/metadata`

分页列表（游标分页）。

**Query 参数**:
- `limit`: int，默认 50，最大 500
- `cursor`: str，上次响应末尾的游标（用于翻页）
- `visibility`: str，过滤可见性
- `include_embedding`: bool，默认 false

**响应**:
```json
{
  "items": [...],
  "next_cursor": "...",
  "total": 150
}
```

#### `GET /records/{record_id}`

获取单条技能详情，含 parent_ids。

#### `GET /records/{record_id}/download`

下载技能的 ZIP 包（二进制流，Content-Type: application/zip）。

---

### Search（混合搜索）

#### `GET /search?q=<query>&limit=20`

混合搜索（语义 + 全文）。

**Query 参数**:
- `q`: 搜索词（必填）
- `limit`: 返回数量，默认 10

**响应**:
```json
{
  "query": "blink LED on Arduino",
  "count": 5,
  "search_type": "hybrid",
  "results": [
    {
      "record_id": "...",
      "name": "...",
      "description": "...",
      "score": 0.87,
      "match_type": "semantic"
    }
  ]
}
```

**内部逻辑**:
1. 若配置了 `EMBEDDING_API_KEY`：生成 query embedding，pgvector 余弦相似度（权重 0.6）+ PostgreSQL FTS（权重 0.4），合并重排序
2. 若未配置 embedding：仅 FTS，search_type 标记为 `fts_only`

---

### Evolutions（技能演化 / PR 工作流）

这是平台核心功能，模拟 GitHub PR 流程。

#### `POST /evolutions`

提交演化提案。

**请求体**:
```json
{
  "artifact_id": "...",
  "parent_skill_id": "...",
  "origin": "fixed",
  "proposed_name": "...",
  "proposed_description": "...",
  "change_summary": "修复了 XXX 问题",
  "proposed_by": "agent-id"
}
```

**内部状态机**:
```
  POST /evolutions
        │
        ▼
   [evaluating]
        │
   ┌────┴────────────┐
score<0.3  0.3-0.6  score≥0.6
   │          │          │
[rejected] [pending] [accepted]
              │
         POST /accept → [accepted]
         POST /reject → [rejected]
```

**质量评估**（`evaluator.py`，6 项检查）：

| 检查项 | 规则 |
|--------|------|
| has_name | proposed_name ≥ 3 字符，无路径分隔符 |
| has_description | proposed_description ≥ 10 字符 |
| has_body | SKILL.md 去掉 frontmatter 后 body ≥ 20 字符 |
| lineage_valid | fixed/derived 类型必须提供 parent_skill_id |
| change_explained | fixed/derived 类型必须提供 change_summary |
| no_dangerous_patterns | 内容不含 `rm -rf`、`os.system`、`eval(`、`exec(`、`subprocess`、`DROP TABLE` |

- **quality_score** = 通过项数 / 总项数
- **passed** = quality_score ≥ 0.5 AND has_name 通过 AND 无危险模式
- score ≥ 0.6 → 自动 accept，创建 SkillRecord，auto_accepted = true

#### `GET /evolutions/{evolution_id}` — 查看单条演化

#### `GET /evolutions` — 列表（支持按 status、parent_skill_id 过滤）

#### `POST /evolutions/{evolution_id}/accept` — 人工 accept

仅 pending 状态可 accept，自动创建对应 SkillRecord，更新 result_record_id。

#### `POST /evolutions/{evolution_id}/reject`

**请求体**: `{"reason": "内容不符合要求"}`

---

### Runs（执行记录）

#### `POST /runs` — 创建执行记录

**请求体**:
```json
{
  "skill_id": "org/my-skill/v1",
  "task": "在 Arduino 上闪烁 LED",
  "executor_type": "reasoning",
  "target_env": {
    "board_type": "Arduino Uno",
    "interface": "USB",
    "architecture": "AVR"
  },
  "context": {"user": "agent-1"}
}
```

响应含 `run_id`，status 初始为 `running`。

#### `GET /runs/{run_id}` — 查询执行状态

#### `PATCH /runs/{run_id}` — 更新执行结果

**请求体**:
```json
{
  "status": "success",
  "result": "LED 已成功闪烁 10 次",
  "error": null,
  "run_log": "执行日志..."
}
```

---

## 7. 后端服务层详解

### `skill_parser.py` — 技能文档解析

```python
parse_skill_md(zip_bytes: bytes) -> dict
```

1. 从 ZIP bytes 中找到 `SKILL.md`（路径不限）
2. 解析 YAML frontmatter（`---` 之间的内容）
3. 提取：`name`、`description`、`tags`
4. 剩余部分作为 `body`
5. 若 ZIP 损坏或无 SKILL.md → 返回空 dict

**SKILL.md 格式示例**:
```markdown
---
name: Blink LED
description: 控制 Arduino 上的 LED 闪烁
tags: [arduino, hardware, LED]
---

## 使用说明

本技能通过 USB 串口控制 Arduino Uno 板的 LED...
```

### `embedding.py` — 语义向量生成

```python
async generate_embedding(text: str) -> Optional[list[float]]
build_embedding_text(name, description, tags) -> str
```

- 调用 OpenAI 兼容 API（支持 Ollama、vLLM 等本地模型）
- 输入文本格式：`"{name} | {description} | tags: {tag1}, {tag2}"`
- 若 `EMBEDDING_API_KEY` 未设置 → 返回 None（系统降级为纯 FTS 搜索）
- 支持配置：API Base、Model、Dimensions

### `search.py` — 纯 Python 混合搜索（降级用）

```python
search_records(query, candidates, query_embedding, limit, weights) -> list[dict]
```

BM25 分数（权重 0.4）+ 余弦相似度（权重 0.6），作为 pgvector 不可用时的降级实现。

### `evaluator.py` — 演化质量评估

```python
evaluate_evolution(...) -> EvaluationResult
```

返回：
```python
{
  "passed": True,
  "quality_score": 0.83,
  "notes": ["has_name: pass", "no_dangerous_patterns: pass"],
  "checks": {
    "has_name": True,
    "has_description": True,
    "has_body": True,
    "lineage_valid": True,
    "change_explained": False,
    "no_dangerous_patterns": True
  }
}
```

---

## 8. MCP Server 详解

**文件**: `backend/mcp_server.py`
**协议**: MCP stdio（Model Context Protocol）
**用途**: 让 AI Agent（如 Claude）直接通过 MCP 工具调用平台功能，无需手写 HTTP 请求

### 启动方式

```bash
cd backend
python mcp_server.py
```

或在 Claude Code `settings.json` 中配置为 MCP server。

### 7 个 MCP Tools

---

#### `search_skills`

按语义/关键词搜索技能库。

**参数**: `query`（必填）, `limit`（默认 10）, `domain`（可选过滤）, `risk_level`（可选过滤）

**返回**: `{query, count, search_type, results[]}`

---

#### `get_skill`

获取技能完整内容（含 SKILL.md 和 skill.yaml 原文）。

**参数**: `skill_id`（必填）

**返回**: `{skill_id, name, description, origin, tags, skill_md, skill_yaml, parents}`

---

#### `execute_task`

执行一个技能（Reasoning 层，返回指令而非真正运行代码）。

**参数**: `task`（必填）, `skill_id`（可选，不填自动搜索）, `context`（可选）, `target_env`（可选）

**内部逻辑**:
1. 若未指定 skill_id → 用 task 搜索匹配的技能
2. 创建 ExecutionRun 记录（status=running）
3. 返回技能指令（SKILL.md 内容供 Agent 参考执行）
4. Agent 执行完后应调用 `PATCH /runs/{run_id}` 更新结果

**返回**: `{status, run_id, skill_id, skill_name, instructions}`

---

#### `submit_skill_revision`

提议修改一个已有技能（类似 GitHub PR）。

**参数**: `skill_id`（必填）, `skill_md`（必填）, `rationale`（必填）, `skill_yaml`（可选）

**内部逻辑**: 打包 ZIP → stage artifact → propose evolution（origin=fixed）

**返回**: `{evolution_id, status, auto_accepted, result_skill_id, evaluation}`

---

#### `publish_skill`

发布一个全新技能（captured origin）。

**参数**: `name`（必填）, `description`（必填）, `body`（必填）, `tags`（可选）, `skill_yaml`（可选）

**内部逻辑**: 自动组装 SKILL.md → stage artifact → propose evolution（无 parent）

**返回**: `{evolution_id, status, skill_id, auto_accepted}`

---

#### `get_skill_lineage`

查看技能的祖先和后代关系树。

**参数**: `skill_id`（必填）

**返回**: `{skill_id, name, parents, children[], total_evolutions}`

---

#### `get_execution_log`

查询一次执行记录的详情。

**参数**: `run_id`（必填）

**返回**: 完整 ExecutionRun 对象（含 run_log、result、error 等）

---

## 9. 前端详解

### 页面路由

| 路径 | 文件 | 功能 |
|------|------|------|
| `/` | `src/app/page.tsx` | 技能注册表首页（列表 + 搜索）|
| `/skills/[id]` | `src/app/skills/[id]/page.tsx` | 技能详情页 |

### 首页（`page.tsx`）

- 启动时调用 `listAllRecords()` 分页加载所有技能（每次 48 条）
- 客户端 TF 搜索（基于已加载的数据）
- 过滤器：`visibility`（public/group_only）、`level`（workflow/tool_guide/reference）
- 技能数量统计（过滤后/全部）
- 点击"Load More"加载更多

### 技能详情页（`skills/[id]/page.tsx`）

**三个 Tab**:

1. **Overview（概览）**
   - tags 列表、元数据（创建者、时间、fingerprint、可见性、层级）
   - 变更说明（change_summary）
   - 父技能快速链接

2. **Lineage（血缘图）**
   - 力导向图（`LineageGraph.tsx`）
   - 节点颜色：灰色=祖先（BFS 向上 3 层）、蓝色=当前、橙色=子节点、琥珀色=孙子节点
   - 点击节点跳转对应技能详情
   - 同时展示父/子节点文字列表

3. **Diff（差异）**
   - Unified diff 查看器（`DiffViewer.tsx`）
   - 若 content_diff 为空则不显示此 tab
   - 支持多文件展开/折叠

**操作**: 下载 ZIP 按钮 → 调用 `/records/{id}/download`

### 组件详解

#### `SearchBar.tsx`

搜索框，带图标和清除按钮的受控输入框，onChange 回调。

#### `SkillCard.tsx`

显示：技能名/ID、描述（2行截断）、level/origin/visibility 彩色 badge、前 6 个 tags（超出显示 +N）、创建者和时间。

Badge 颜色规则：
- level: `workflow`→紫色，`tool_guide`→蓝色，`reference`→绿色
- origin: `captured`→青色，`fixed`→黄色，`derived`→橙色
- visibility: `public`→绿色，`group_only`→黄色，`private`→红色

#### `LineageGraph.tsx`

调用 `GET /records/metadata` 获取所有技能父子关系，BFS 遍历构建图，react-force-graph-2d 渲染，ResizeObserver 自动适应宽高。

#### `DiffViewer.tsx`

解析 unified diff 格式：`--- a/file`/`+++ b/file` → 文件头，`@@ ... @@` → hunk 标题，`+`→新增行（绿色），`-`→删除行（红色），空格→上下文行（灰色）。

#### `api.ts` — TypeScript API 客户端

```typescript
const client = new XiacheClient({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  apiKey: process.env.NEXT_PUBLIC_API_KEY || 'dev-key-for-testing'
})

// 主要方法
client.health()
client.stageArtifact(files)
client.createRecord(data)
client.getRecord(id)
client.listRecordsMetadata(params)
client.search(query, limit)
client.proposeEvolution(data)
client.getEvolution(id)
client.listEvolutions(params)
client.acceptEvolution(id)
client.rejectEvolution(id, reason)

// 辅助方法（自动翻页，返回 AsyncGenerator）
listAllRecords(client, params)
```

---

## 10. 环境变量与配置

### 后端（`backend/.env.example`）

```env
# 数据库连接（asyncpg 驱动）
DATABASE_URL=postgresql+asyncpg://xiache:xiache@localhost:5432/xiache

# Artifact 文件存储路径
STORAGE_PATH=./data/artifacts

# Embedding（可选，不填则仅 FTS 搜索）
EMBEDDING_API_KEY=                        # 留空 = 不使用 embedding
EMBEDDING_API_BASE=                        # 留空 = OpenAI 默认; 可填本地 Ollama 地址
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# 安全配置
SECRET_KEY=change-me-in-production-random-string-here
CORS_ORIGINS=["*"]                         # 生产环境改为具体域名

# 开发模式（关闭后使用数据库 api_keys 表鉴权）
XIACHE_DEV_MODE=true
DEV_API_KEY=dev-key-for-testing

# 分页配置
DEFAULT_PAGE_LIMIT=50
MAX_PAGE_LIMIT=500

# 演化自动接受阈值（0.0–1.0）
AUTO_ACCEPT_THRESHOLD=0.6
```

### 前端环境变量

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key-for-testing
```

在 Docker Compose 中通过 `build.args` 注入（构建时固定）。

### Docker Compose 端口配置（通过 `.env` 覆盖）

```env
POSTGRES_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

---

## 11. 核心业务逻辑

### 去重机制

发布技能时有两层去重：

1. **record_id 去重**：若指定的 record_id 已存在 → 报错 409
2. **内容指纹去重**：若 content_fingerprint（SHA256）已存在 → 报错 409

### Artifact 存储分片

```python
path = f"{STORAGE_PATH}/{artifact_id[:2]}/{artifact_id}.zip"
```

UUID 前两位作为子目录（类似 Git 的 object storage），避免单目录文件过多。

### 演化工作流完整时序

```
Agent                    Platform                       数据库
  │                         │                              │
  │─── stage artifact ──────▶                              │
  │                         │── INSERT artifacts ─────────▶│
  │◀── artifact_id ─────────│                              │
  │                         │                              │
  │─── POST /evolutions ────▶                              │
  │                         │── evaluate_evolution()       │
  │                         │   (6 checks, 同步运行)        │
  │                         │── INSERT skill_evolutions ──▶│
  │                         │   status=evaluating          │
  │                         │                              │
  │                         │── [if score≥0.6]             │
  │                         │   INSERT skill_records ─────▶│
  │                         │   INSERT skill_lineage ─────▶│
  │                         │   UPDATE evolutions ─────────▶│
  │                         │   status=accepted            │
  │◀── evolution response ──│                              │
```

### 混合搜索流程

```
查询词 "blink LED Arduino"
        │
        ├─── 生成 query embedding（OpenAI 兼容 API）
        │         │
        │         ▼
        │    pgvector 余弦相似度召回（取 limit×5 候选）
        │
        └─── PostgreSQL FTS（tsvector @ tsquery）召回

合并两路结果 → 按加权分数排序 → 返回 Top-K
最终分数 = 0.6 × semantic_score + 0.4 × fts_score
```

### API 鉴权流程

```python
# deps.py
async def get_current_api_key(authorization: str):
    token = authorization.removeprefix("Bearer ")

    if settings.XIACHE_DEV_MODE:
        if token == settings.DEV_API_KEY:
            return token
        raise HTTPException(401)

    # 生产模式：SHA256 查库
    key_hash = sha256(token)
    record = await db.query(ApiKey).filter_by(key_hash=key_hash, is_active=True)
    if not record:
        raise HTTPException(401)
    return record
```

---

## 12. 部署指南

### 快速启动（Docker Compose）

```bash
# 1. 克隆仓库
git clone <repo-url>
cd xiache

# 2. 一键启动（推荐）
make bootstrap
# 会自动：
# - 在 .env 不存在时从 .env.example 创建
# - 启动/构建全部服务
# - 在容器内执行数据库初始化 SQL

# 3. 查看日志
make logs

# （可选）如果你想手动控制，也可以不用 bootstrap：
cp .env.example .env
# 编辑 .env，至少修改 SECRET_KEY
make up
make init-db

# 服务地址：
# 前端：  http://localhost:3000
# 后端：  http://localhost:8000
# API 文档：http://localhost:8000/docs
# 默认 API Key：dev-key-for-testing
```

### Docker Compose 三个服务

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | pgvector/pgvector:pg16 | 5432 | 自动创建 xiache 库和用户，执行 init.sql |
| backend | 本地构建 Python 3.12 slim | 8000 | 依赖 postgres healthy 后启动 |
| frontend | 本地构建 Node 20 alpine | 3000 | 依赖 backend healthy 后启动 |

### 生产环境 Checklist

- [ ] 修改 `SECRET_KEY` 为随机长字符串
- [ ] `XIACHE_DEV_MODE=false`
- [ ] `CORS_ORIGINS` 改为具体域名
- [ ] 配置 `EMBEDDING_API_KEY`（推荐，否则仅 FTS 搜索）
- [ ] 备份 `postgres_data` 和 `artifact_data` 两个 volume
- [ ] 通过 `api_keys` 表管理生产 API Key（SHA256 存储）

### 手动初始化数据库（不用 Docker）

```bash
psql -U postgres -c "CREATE USER xiache WITH PASSWORD 'xiache';"
psql -U postgres -c "CREATE DATABASE xiache OWNER xiache;"
# 下面这条如果带 -h localhost（TCP 连接）通常会要求密码：
PGPASSWORD=xiache psql -U xiache -d xiache -h localhost -f backend/migrations/init.sql
# 不带 -h 时走本机 Unix socket，是否免密取决于你本机 PostgreSQL 的 pg_hba.conf（常见为 peer/trust）
```

如果你使用 Docker Compose，优先用下面这条在容器内执行初始化（避免本机 psql 认证差异）：

```bash
make init-db
# 或一键从零启动：
make bootstrap
```

---

## 13. 开发指南

### 本地开发环境

**后端**:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # 编辑 DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

**前端**:
```bash
cd frontend
npm install
npm run dev
# 前端：http://localhost:3000
```

**MCP Server**:
```bash
cd backend
python mcp_server.py
# 在 Claude Code settings 中配置此 stdio server
```

### 代码入口

- `app/main.py`：FastAPI app 实例，挂载 CORS，include 路由，配置 lifespan（startup/shutdown）
- `app/core/config.py`：`Settings` 类，全局单例 `settings`，从 `.env` 读取所有配置
- `app/core/database.py`：`AsyncSessionLocal`，`get_db()` 依赖注入
- `app/api/v1/router.py`：聚合所有子路由，统一前缀 `/api/v1`

### 新增 API 端点流程

1. `app/schemas/api.py` → 新增 Pydantic 请求/响应模型
2. `app/models/db.py` → 新增 ORM 模型（若需新表）
3. `backend/migrations/init.sql` → 新增建表 SQL
4. `app/api/v1/` → 新建或修改路由文件
5. `app/api/v1/router.py` → include 新路由
6. `backend/mcp_server.py` → 新增 MCP Tool（若需暴露给 Agent）
7. `frontend/src/lib/api.ts` → 新增对应客户端方法

### 技能文件规范（SKILL.md）

每个技能 ZIP 包必须包含 `SKILL.md`：

```markdown
---
name: Blink LED（必填，≥3 字符）
description: 控制 Arduino 上的 LED 闪烁（必填，≥10 字符）
tags:
  - arduino
  - hardware
  - LED
---

## 使用说明（必填，去掉 frontmatter 后 ≥20 字符）

本技能通过 USB 串口控制 Arduino Uno 板的 LED...
```

可选附带 `skill.yaml`（硬件元数据）：
```yaml
id: org/skill-name/v1
intent: 控制 Arduino LED 闪烁
domain: hardware/arduino
hardware_requirements:
  board_type: Arduino Uno
  interface: USB
risk_level: low
permissions:
  - hardware.gpio
execution_backend: physical
```

---

## 14. 扩展路线图

根据 `architectbyOpenspace.md` 设计文档，平台规划三个阶段：

### Phase 1（当前）— 本地闭环
- [x] 技能注册 / 发布 / 搜索
- [x] 演化提案 + 质量评估（6 项自动检查）
- [x] 执行记录（三层模型）
- [x] 血缘追踪（力导向图可视化）
- [x] MCP Server（Agent 可直接调用 7 个工具）

### Phase 2 — 组织级
- [ ] 多租户（organization）支持
- [ ] 基于角色的访问控制（RBAC）
- [ ] 组织内技能共享（group_only visibility）
- [ ] 审计日志
- [ ] Trust Score 自动计算（30 天成功率、自动测试通过率）

### Phase 3 — 公共生态
- [ ] 公共技能注册表（类似 npm/PyPI）
- [ ] Agent 自动提交演化（无人工参与的技能进化闭环）
- [ ] 硬件兼容性矩阵（board_type 过滤匹配）
- [ ] 技能市场 / 发现页面
- [ ] 联邦技能注册表（本地 + 组织 + 公共 分层查找）

---

## 常见问题

**Q: 不配置 Embedding API，搜索还能用吗？**
A: 可以，降级为纯 PostgreSQL 全文搜索（FTS），`search_type` 字段标记为 `fts_only`。

**Q: 技能 ID 的格式有什么规范？**
A: 没有强制格式，推荐 `{org}/{skill-name}/{version}`（如 `myorg/blink-led/v1`）。不填则系统自动生成 UUID。

**Q: 演化被 rejected 后如何重新提交？**
A: 修改内容后重新 stage artifact，提交新的 evolution，旧的 rejected evolution 不影响新提案。

**Q: 如何给 Claude Code 配置 MCP Server？**
A: 在 Claude Code 的 settings.json 中添加 MCP Server 配置，type 为 `stdio`，command 为 `python backend/mcp_server.py`。

**Q: pgvector IVFFLAT 索引在数据量少时有问题吗？**
A: 数据量 < 100 时向量搜索可能走全表扫描，这是正常的，结果仍然正确，只是未使用索引加速。
