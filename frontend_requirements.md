# Frontend Requirements Document — Agent-native Skill Platform

## 1. 文档目的

本文档用于定义 Agent-native Skill Platform 的前端需求，目标是让前端、产品、设计、后端在同一套页面结构、交互语言和信息架构下协作。

参考 GitHub 的交互方式，但适配 Skill / Task / Execution / Review / Device 场景。

---

## 2. 核心设计目标

### 用户需要做到：

* 看懂 Agent 在做什么（透明）
* 控制风险（可控）
* 审核变更（可审）
* 快速找到能力（可发现）

---

## 3. 信息架构（导航）

顶部导航：

* Dashboard
* Skills
* Tasks
* Executions
* Reviews
* Registry
* Devices
* Projects
* Notifications

---

## 4. 核心页面

## 4.1 Dashboard

展示：

* 最近任务
* 失败执行
* 待审批操作
* 更新的 Skills

---

## 4.2 Skills

列表展示：

* 名称 / 描述
* Trust score
* 使用次数
* 成功率
* 风险等级
* 支持设备

详情页必须包含：

* 输入输出
* 执行步骤
* 权限
* lineage
* 示例

---

## 4.3 Task

区分两部分：

* 用户目标
* Agent 计划

---

## 4.4 Execution

必须可视化：

```
Task → Skill → Step → Result
```

包含：

* Timeline
* Logs
* 状态
* 是否涉及真实设备

---

## 4.5 Review（核心）

类似 GitHub PR：

* Diff
* 评论
* 审批
* Merge / Reject

---

## 4.6 Devices（你独有）

展示：

* 在线状态
* 能力
* 最近执行
* 风险

⚠️ 所有真实设备操作必须二次确认

---

## 5. 通用能力

所有列表页必须支持：

* 搜索
* 筛选
* 排序
* Saved views

---

## 6. 状态系统

统一状态：

* Draft
* Running
* Failed
* Success
* Blocked
* Deprecated

---

## 7. 风险分级

* Low
* Medium
* High

涉及硬件必须高亮提示

---

## 8. 核心组件

必须统一：

* Table
* Timeline
* Diff viewer
* Log viewer
* Comment thread
* Approval modal

---

## 9. 权限

角色：

* Visitor
* Member
* Reviewer
* Admin

---

## 10. MVP 页面

P0：

* Dashboard
* Skills
* Task
* Execution
* Review
* Notifications

---

## 11. 一句话总结

> 这个前端不是“展示 AI”，而是“控制 AI”

目标：

👉 像 GitHub 管代码一样
👉 管 Agent 的行为
