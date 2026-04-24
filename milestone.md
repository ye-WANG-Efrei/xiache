# Xiache — Milestone Log

每次有效变更后更新这里。格式：日期 + emoji + 粗体标题 + 一两句说明。

---

## 📢 Updates

- **2026-04-24** 🗂️ **Categories + ZhipuAI embedding-3 接入** — 新增 `GET /categories` 端点，skill 注册时自动写入语义分类原型（向量中心点增量更新）。向量维度从 1536 → 2048，对接智谱 AI `embedding-3` 免费模型（OpenAI 兼容协议，零额外依赖）。顺手修复了 `search.py` 和 `category.py` 中 asyncpg 不支持 `:param::vector` 语法导致的 500 错误。Smoke test 更新至 T1–T7 全覆盖。

- **2026-04-23** 🔀 **REST 路由重命名 `/records → /skills`** — 统一 API 语义，路由前缀、handler 名、前端 API 调用、MCP server URL 全部同步更新，数据库表名和业务逻辑不变。

- **2026-04-22** 🧹 **移除 ZIP/Artifact 层，Skill 内容直存 DB** — 去掉两步上传流程（stage artifact → create record），改为单次 `POST /skills` JSON 直传。简化了注册流程，消除了磁盘依赖，内容指纹去重保留。

- **2026-04-21** 🌐 **CORS + 环境变量修复** — 解决浏览器跨域问题，API 调用通过 Next.js proxy 转发；清理 Dockerfile 和 `.env.example` 中硬编码的 `NEXT_PUBLIC_API_URL` 默认值；`make up` 现在自动读取实际映射端口并打印本机 IP。

- **2026-04-19** ✅ **Sprint 1 单元测试套件** — 50 项测试全部通过，覆盖 skill 存储、11 项 evaluator 检查、evolution 血缘机制、OpenSpace 执行数据 ingest。测试过程中发现并修复 5 个 bug（事务安全、冲突检测、循环防护、注入加固）。

- **2026-04-18** 🚀 **核心功能上线** — Skill 结构化存储（name / description / body / tags / schema）、Evolution 提案机制（11 项 evaluator 自动评分）、auto-accept 阈值、血缘图、OpenSpace 执行数据 ingest、LLM 驱动自演化 pipeline。

- **2026-04-17** 🏗️ **一键启动 & 数据库 bootstrap** — `make up` 单命令拉起全栈（Postgres + pgvector + FastAPI + Next.js）；`make bootstrap` 自动建库建表；`docker-compose` 健康检查确保启动顺序。
