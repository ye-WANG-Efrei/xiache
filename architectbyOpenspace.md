# Architect by OpenSpace

## 1. 背景与判断

基于对 HKUDS OpenSpace 开源项目的公开设计思路观察，可以得出一个很直接的结论：

**真正有效的，不是单独的 MCP 接入，而是 MCP + Host Skills + Skill Registry + Execution Loop + Skill Evolution 的闭环。**

这意味着，如果我们的目标是构建一个 **Agent-native、面向嵌入式与硬件场景的开源平台**，那么就不能只做一个“把能力包装成 MCP 工具”的平台。那样只能做到“可接入”，做不到“可理解、可组合、可演化、可治理”。

因此，平台设计目标不应是：

- 做一个 MCP Tool 集合
- 做一个 API Marketplace
- 做一个给人看的技能文档仓库

而应当是：

- 做一个 **Agent-native Skill Runtime**
- 做一个 **可发现、可执行、可修复、可派生、可治理的 Skill 平台**
- 做一个 **硬件感知（hardware-aware）的 Agent 能力操作系统**

---

## 2. 从 OpenSpace 得到的核心启发

OpenSpace 给出的关键启发不是“Agent 会自动发现并完美调用工具”，而是：

### 2.1 MCP 只是入口层
MCP 的作用是标准化工具暴露方式，让兼容的 Agent 可以看见并调用工具。

但 MCP 本身并不负责：

- 自动选择最优工具
- 自动规划复杂流程
- 自动理解垂直行业语义
- 自动保证执行结果可靠

所以，**MCP 是接入标准，不是平台壁垒。**

### 2.2 Host Skills 非常关键
OpenSpace 的实践说明，只暴露 MCP 工具还不够。还需要通过 Host Skills 教会 Agent：

- 什么时候先搜索 skill
- 什么时候委托执行
- 什么时候修复已有 skill
- 什么时候沉淀新 skill

这说明：

> Agent 能不能稳定地“用对工具”，取决于额外的技能组织层，而不只是工具本身。

### 2.3 Skill 不是静态资产，而是可演化资产
OpenSpace 中 skill 的价值不只是被调用，还包括：

- 修复（Fix）
- 派生（Derive）
- 捕获（Capture）
- Lineage 跟踪
- 差异比较

这一点非常重要。它意味着平台不能把 skill 当成静态模板，而应该把它视为一个持续演进的能力单元。

### 2.4 对我们更重要的是治理
OpenSpace 的方向适合做通用 Agent 技能平台，但如果进入生产环境，尤其是嵌入式、板卡、固件、设备控制场景，平台必须补上：

- 权限边界
- 执行隔离
- 风险分级
- 沙箱验证
- 审计追踪
- 版本可信度

否则平台会很快从“可进化”变成“不可控”。

---

## 3. 我们的平台目标定义

我们的平台不是一个通用 AI 工具市场，而是：

> **一个面向 Agent 的、垂直于嵌入式与硬件解决方案的开源能力平台。**

平台需要具备以下目标能力：

1. 让 Agent 能发现并理解 Skill
2. 让 Agent 能执行并组合 Skill
3. 让 Agent 能在真实执行中沉淀经验
4. 让 Skill 能被修复、派生、复用与治理
5. 让开发者社区围绕 Skill 形成生态
6. 最终让平台能力与硬件载体、小板、运行环境形成绑定

换句话说，平台的商业和技术闭环应该是：

**高质量 Skill → Agent 使用平台 → 社区形成 → 运行环境标准化 → 硬件载体绑定 → 生态壁垒形成**

---

## 4. 总体架构原则

平台架构应遵循以下原则：

### 4.1 MCP 必须有，但只能作为入口
MCP 是生态兼容层，不应被当作核心产品本身。

### 4.2 Skill 必须结构化
不能只用自然语言描述 skill，而要让 skill 具备明确的机器可理解结构。

### 4.3 执行必须分层
必须区分：

- 推理执行
- 软件环境执行
- 设备/板卡执行

### 4.4 进化必须受治理
Skill 的修复、派生、捕获必须可审计、可回滚、可比较。

### 4.5 平台必须硬件感知
因为我们的垂直方向是 embedded / board / chip / industrial workflow，所以 skill 的执行条件必须包含硬件和环境约束。

---

## 5. 推荐总体架构

```text
                    ┌─────────────────────────────┐
                    │        Agent Clients         │
                    │ Claude / OpenClaw / Codex   │
                    │ Internal Agent / SDK / CLI  │
                    └─────────────┬───────────────┘
                                  │
                         MCP / SDK / Host Skills
                                  │
                    ┌─────────────▼───────────────┐
                    │      Agent Access Layer      │
                    │ MCP Server + Host Skills     │
                    │ Tool Schemas + Adapters      │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │      Skill Runtime Layer     │
                    │ Structured Skill Spec        │
                    │ Workflow / Preconditions     │
                    │ Permission / IO Schema       │
                    │ Hardware-aware constraints   │
                    └─────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
┌────────▼────────┐    ┌─────────▼─────────┐    ┌────────▼────────┐
│ Skill Registry   │    │ Execution Engine   │    │ Evolution Engine │
│ Local / Org /    │    │ Planner / Router   │    │ Fix / Derive /   │
│ Public Registry  │    │ Sandbox / Runtime  │    │ Capture / Review │
│ Search / Ranking │    │ Device Connectors  │    │ Lineage / Scores │
└────────┬────────┘    └─────────┬─────────┘    └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │ Governance & Observability   │
                    │ Auth / ACL / Audit / Logs    │
                    │ Metrics / Replay / Diff UI   │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │ Device / Board / Cloud Env   │
                    │ MCU / Linux board / Gateway  │
                    │ CI / Simulator / Test Bench  │
                    └──────────────────────────────┘
```

---

## 6. 分层设计说明

## 6.1 Agent Access Layer

这一层的职责是让不同 Agent 接入平台。

### 组成
- MCP Server
- Host Skills
- SDK
- CLI
- Agent Adapter

### 作用
- 暴露统一工具接口
- 给 Agent 注入平台能力使用方式
- 降低不同 Agent 的接入门槛

### 设计建议
这一层至少应提供：

- `search_skills`
- `execute_task`
- `submit_skill_revision`
- `publish_skill`
- `get_skill_metadata`
- `get_skill_lineage`

同时配套提供两个官方 Host Skills：

- `skill-discovery`
- `delegate-task`

它们不是业务 skill，而是“教 Agent 如何使用平台”的系统 skill。

---

## 6.2 Skill Runtime Layer

这是平台的核心语义层。

Skill 不能只是一个 Markdown 文档，而应该是“文档 + 结构化规范 + 可执行约束”的复合体。

### 推荐 Skill 包结构

```text
skill/
├── skill.yaml
├── SKILL.md
├── examples/
├── tests/
├── assets/
└── lineage.json
```

### 推荐 skill.yaml 字段

```yaml
id: embedded.ota.diagnosis.v1
name: OTA Failure Diagnosis
intent: Diagnose OTA upgrade failures on supported boards
version: 1.0.0
owner: official
visibility: public

domain:
  - embedded
  - ota
  - board-maintenance

hardware_requirements:
  board_types:
    - linux_gateway
    - stm32_devkit
  interfaces:
    - uart
    - ssh
    - can
  architecture:
    - arm64
    - armv7

required_inputs:
  - device_id
  - firmware_version
  - connection_type

optional_inputs:
  - log_bundle
  - board_model
  - last_upgrade_time

preconditions:
  - device reachable
  - permission:device.read

permissions:
  - device.read
  - logs.read

execution_backend:
  mode: hybrid
  supports_simulation: true
  supports_real_device: true

steps:
  - collect logs
  - inspect connectivity
  - verify image compatibility
  - compare firmware metadata
  - classify failure type
  - recommend remediation

verification:
  success_signals:
    - root_cause_identified
    - remediation_generated
  tests:
    - simulator_case_1
    - simulator_case_2

risk_level: medium
cost_profile: low
output_schema:
  type: diagnosis_report
```

### 为什么必须结构化
因为 Agent 在嵌入式场景里不能只靠“猜”。

它必须知道：

- 当前 skill 适不适合这个板子
- 当前执行需不需要真实设备权限
- 这个 skill 是读操作还是写操作
- 能不能先在仿真环境验证
- 输出格式是什么

只有这样，平台才能从“提示工程系统”升级为“能力操作系统”。

---

## 6.3 Skill Registry Layer

这一层负责 skill 的存储、检索、分发与排名。

### 推荐三层 Registry

#### 1. Local Registry
用于当前工作区、本地工程、单机开发环境。

#### 2. Organization Registry
用于企业内团队、项目组、产品线内部共享。

#### 3. Public Community Registry
用于公共开源社区、开发者生态和分发。

### Skill 搜索不能只靠关键词
建议采用混合搜索：

- semantic search
- tag / ontology search
- hardware compatibility filter
- protocol filter
- permission filter
- trust score ranking

### 典型检索逻辑
用户说：

> “帮我给这块工业传感器板做 OTA 故障诊断。”

平台不应只根据 “OTA” 检索，而应进一步筛选：

- 是否支持当前板型
- 是否支持当前接口
- 是否需要写权限
- 是否可在 simulator 先运行
- 当前 skill 是否可信

### 建议底层实现
- Metadata: Postgres
- Vector Search: pgvector 或 Qdrant
- Skill 文件存储: Git + Object Storage
- 搜索排序: semantic score + trust score + compatibility score

---

## 6.4 Execution Engine

这是决定平台体验的关键层。

平台不应只做“调用工具”，而应支持完整执行闭环：

### 执行器分三类

#### A. Reasoning Executor
负责：
- 任务拆解
- 计划生成
- 文档解释
- 配置生成
- 代码生成

#### B. Digital Executor
负责：
- shell
- container
- compiler
- CI pipeline
- simulator
- repo 操作

#### C. Physical / Device Executor
负责：
- 串口设备连接
- SSH 到边缘设备
- 固件上传
- 设备状态采集
- 硬件在环测试

### 推荐执行流程
1. 接收任务
2. 解析意图
3. 搜索 skill
4. 选择 skill 或组合多个 skill
5. 校验环境、权限、硬件兼容性
6. 在 sandbox / simulator 先执行
7. 通过后执行真实设备任务
8. 收集日志、状态、输出产物
9. 验证结果
10. 成功则沉淀经验，失败则进入修复流程

### 为什么必须这样设计
因为 embedded 场景不是纯软件场景。很多操作是高风险的：

- 刷写固件
- 控制设备
- 修改配置
- 重启服务
- 下发 OTA

如果没有预校验和沙箱，你的平台会非常脆弱。

---

## 6.5 Evolution Engine

这是平台的长期壁垒来源。

### Skill 进化应支持三类事件

#### 1. Fix
已有 skill 存在问题，需要修复。

#### 2. Derive
从通用 skill 派生出某板型、某项目、某客户专用版本。

#### 3. Capture
从一次真实执行中提炼出新 skill。

### 平台必须记录 lineage
每个 skill 都应记录：

- 父 skill
- 子 skill
- 修改原因
- diff
- 测试结果
- 成功率变化
- 引用关系

### 但进化不能无约束
必须有：

- Review Gate
- Approval Policy
- Auto Test
- Rollback
- Trust Score

### Trust Score 建议指标
- 最近 30 天成功率
- 被调用次数
- 覆盖设备数
- 自动测试通过率
- 最近更新时间
- 是否官方认证
- 是否通过安全审计

---

## 6.6 Governance & Observability

如果你要让平台真正走向企业级或工业级，这一层必须尽早设计。

### 治理能力
- 用户认证
- 组织与项目级 RBAC
- Skill 可见性控制
- 权限声明与审批
- 风险分级策略
- 产物签名与来源追踪

### 可观测能力
- 每次执行的任务日志
- Skill 使用轨迹
- 失败回放
- 参数 diff
- 设备状态时间线
- lineage 可视化

### 必须回答的问题
- 谁在什么时间调用了什么 skill？
- 调用了哪个版本？
- 对哪个设备产生了影响？
- 是否经过审批？
- 能否回滚？

这些问题答不上来，平台就不能上生产。

---

## 7. 与 OpenSpace 的关键差异化定位

OpenSpace 的方向说明了 Agent-native 平台的可能性，但我们的目标必须比它更聚焦、更工程化。

### OpenSpace 更像
- 通用 Agent 技能社区
- 任务委托与技能复用平台
- 通过 MCP + host skills 实现平台接入
- 强调技能共享与技能进化

### 我们的平台应该更像
- 面向嵌入式、板卡、协议、工业流程的 Agent-native 平台
- 带硬件感知的 skill runtime
- 带真实设备执行能力的 orchestration system
- 带治理、审核、可信度体系的生产级 skill 平台

一句话概括：

> **OpenSpace 是通用 Agent Skill Community 的原型；我们的目标是 Embedded Agent Capability OS。**

---

## 8. MVP 设计建议

不要一开始就做“大而全社区”，应先做最小闭环。

## Phase 1：最小闭环

### 目标
让 Agent 能：
- 搜 skill
- 运行 skill
- 执行任务
- 失败后提交修订版
- 人工审核后替换

### 建议功能
- `yourplatform-mcp`
- Skill Schema v1
- Local Registry
- `search_skills`
- `execute_task`
- `submit_skill_revision`
- execution log
- manual review

### 输出结果
你会得到一个：

> 能运行、能修 skill、能保留 lineage 的本地 Agent-native skill runtime

---

## Phase 2：组织化能力

### 增加功能
- Organization Registry
- Trust Score
- Simulator Integration
- Skill Diff UI
- Lineage Graph
- Team Review Workflow

### 输出结果
形成企业内部可共享的 skill 平台。

---

## Phase 3：公共生态

### 增加功能
- Public Community Registry
- Skill Upload / Download
- Auto Benchmark
- Skill Ranking
- Official Verified Skills
- Hardware Bundle Recommendation

### 输出结果
形成社区冷启动能力，并把技能生态与硬件载体绑定。

---

## 9. 推荐 MCP Tool 列表

平台对外的 MCP 工具，不宜过多，先控制在少量高价值工具上。

### 核心工具
- `search_skills(query, constraints)`
- `get_skill(skill_id)`
- `execute_task(task, context, target_env)`
- `submit_skill_revision(skill_id, patch, rationale)`
- `publish_skill(skill_package)`
- `get_skill_lineage(skill_id)`
- `get_execution_log(run_id)`

### 后续扩展工具
- `simulate_skill(skill_id, env)`
- `evaluate_skill(skill_id, benchmark)`
- `compare_skills(skill_a, skill_b)`
- `request_execution_approval(action)`

原则是：

**Agent 看到的工具少，但工具背后的运行时足够强。**

---

## 10. 技术选型建议

### 接入层
- MCP：面向 Agent 生态接入
- Python SDK：面向开发者与内部调用
- CLI：面向工程师与 CI
- REST/gRPC：面向平台内部服务通信

### 数据层
- Postgres：存元数据
- pgvector / Qdrant：向量检索
- S3 / MinIO：Skill 包与执行产物
- Git：版本与 lineage 基础设施

### 执行层
- Temporal / Celery / Arq：任务编排
- Docker / Firecracker：沙箱执行
- QEMU / simulator：板级仿真
- Edge daemon：设备侧执行代理

### 治理层
- OIDC / OAuth2
- RBAC / ABAC
- 审计日志
- Artifact 签名
- 执行审批流

---

## 11. 最终结论

从 OpenSpace 可以学到的最重要一点，不是“把平台包装成 MCP”，而是：

> **平台必须同时解决接入、理解、执行、进化、治理五个问题。**

因此，我们的架构方向应该是：

### 不做什么
- 不只做 API 集合
- 不只做 MCP server
- 不只做 prompt skill 仓库

### 要做什么
- 做结构化 skill runtime
- 做硬件感知的执行系统
- 做可修复可派生的演化闭环
- 做有治理和可信度体系的 skill registry
- 做 Agent-native 的平台入口与生态网络

最终，平台的真正壁垒不是：

> “Agent 能接进来。”

而是：

> **“Agent 能在真实硬件场景下，稳定、可靠、可审计地完成任务，并把经验沉淀成新的平台能力。”**

这才是一个真正值得做的 Agent-native Embedded Platform。
