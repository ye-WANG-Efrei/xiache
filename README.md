# Xiache — Agent-Native Skill Registry

<p align="center">
  <b>GitHub for AI Agent Skills</b><br/>
  Register · Version · Evolve · Review · Log
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.14-blue" />
  <img src="https://img.shields.io/badge/FastAPI-async-green" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-blueviolet" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" />
</p>

---

## 🔔 最新动态

- **2026-04-23** — API 路由统一为 `/api/v1/skills`，移除 artifact 上传层，Skill 内容直接写入数据库
- **2026-04-09** — Sprint 1 完成：Skill 注册 / 进化 / 评估 / 自动演化全链路上线，单元测试 50/50 通过
- **2026-04-09** — 接入 [OpenSpace](https://github.com/HKUDS/OpenSpace) 执行数据，支持从 Agent 执行反馈自动触发 Skill 进化

---

## 是什么

Xiache 是一个面向 AI Agent 的**技能注册中心**


每个 Skill 以 `name + description + body` 直接存入数据库，支持语义向量检索、版本血缘追溯和自动进化。

---

## 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.14+（本地开发）

 ## 启动服务                                                      
                                          
```bash                                                          
git clone https://github.com/ye-WANG-Efrei/xiache.git            
cd xiache
```
> [!TIP]
> 第一次启动，
> 使用 `make bootstrap`：                             
> - 自动从 .env.example 创建 .env（仅在不存在时）
> - 构建并启动全部容器
> - 自动初始化数据库
> ```bash
> make bootstrap
> ```


> [!TIP]
> 日常启动，使用` make up`：
> make up 启动成功后访问：
>- 前端：http://localhost:3000
>- 后端 API：http://localhost:8000
>- API 文档：http://localhost:8000/docs




服务默认运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

---
### 关闭服务  

```
make down
```
---
## 核心工作流

### 1. 注册一个 Skill

直接 POST，一步完成：

```bash
curl -X POST http://localhost:8000/api/v1/skills \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "blink_led_v1",
    "name": "Blink LED",
    "description": "Blink an LED once when triggered by the agent",
    "body": "## Steps\n1. Validate pin range 1-40\n2. Send GPIO HIGH 200ms\n3. Send GPIO LOW\n4. Return {status: ok}",
    "version": "1.0.0",
    "tags": ["iot"],
    "origin": "captured"
  }'
```

### 2. 提交进化提案

```bash
curl -X POST http://localhost:8000/api/v1/evolutions \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "blink_led_v2",
    "description": "Blink LED with pin validation",
    "body": "## Steps\n1. Validate pin range\n2. Blink\n3. Return status",
    "parent_skill_id": "blink_led_v1",
    "origin": "fixed",
    "change_summary": "Added pin range validation and error handling"
  }'
```

Evaluator 自动打分（11 项检查），高分自动 accepted，中分进入 pending 等待人工审核，危险内容直接 rejected。

### 3. 接入 OpenSpace 执行数据（自动进化）

```bash
curl -X POST http://localhost:8000/api/v1/ingest/openspace \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-001",
    "timestamp": "2026-04-09T12:00:00Z",
    "task_completed": false,
    "execution_note": "Agent failed to validate pin range",
    "skill_judgments": [
      {"skill_id": "blink_led_v1", "skill_applied": false, "note": "pin out of range"}
    ],
    "analyzed_by": "openspace-v0.1",
    "analyzed_at": "2026-04-09T12:00:01Z"
  }'
```

当 fallback_rate > 40% 或 completion_rate < 35%（最少 5 次执行），系统自动调用 LLM 改写 SKILL.md 并提交进化提案。

---

## API 概览

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/skills` | 注册 Skill |
| `GET` | `/api/v1/skills/{id}` | 获取 Skill 详情 |
| `GET` | `/api/v1/skills/metadata` | 列出所有 Skills（分页） |
| `GET` | `/api/v1/skills/{id}/download` | 下载 Skill 为 Markdown |
| `POST` | `/api/v1/evolutions` | 提交进化提案 |
| `POST` | `/api/v1/evolutions/{id}/accept` | 手动接受 |
| `POST` | `/api/v1/evolutions/{id}/reject` | 手动拒绝 |
| `POST` | `/api/v1/ingest/openspace` | 接入 OpenSpace 执行数据 |
| `GET` | `/api/v1/search` | 语义搜索 Skill |

完整文档见 `/docs`（Swagger UI）。

---

## 配置

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/xiache
API_KEY=your-api-key

# 自动进化（可选）
LLM_API_KEY=sk-...
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
AUTOEVO_FALLBACK_RATE=0.40
AUTOEVO_COMPLETION_RATE=0.35
AUTOEVO_MIN_SELECTIONS=5
```

---

## License

MIT
