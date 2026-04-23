# Xiache Smoke Test

**环境**: `make up` 启动后  
**工具**: WSL 终端（curl）+ 浏览器  
**API Key**: `dev-key-for-testing`  
**Base URL**: `http://localhost:8000`

---

## 前置：设置变量

在 WSL 终端里执行一次，后面所有命令直接复制粘贴：

```bash
BASE="http://localhost:8000"
KEY="dev-key-for-testing"
```
>[!tip]
>这是在设置环境变量（shell 变量），后面的命令可以直接用 $BASE 和 $KEY 引用，避免每次都手打完整地址和密钥。
> `curl -s $BASE/api/v1/health `
> 等价于
> `curl -s http://localhost:8000/api/v1/health`


---

## T1 — 健康检查

```bash
curl -s $BASE/api/v1/health | python3 -m json.tool
```

**期望**：
```json
{ "status": "ok", "database": "ok" }
```

**判断逻辑**：`status` 和 `database` 都是 `"ok"` 才通过。

---

## T2 — 注册 Skill（JSON 直传）

`record_id` 可选——不传时后端自动从 `name` 生成 slug：

```bash
curl -s -X POST $BASE/api/v1/skills \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hello_skill",
    "description": "prints hello to the terminal",
    "body": "## Steps\n1. Run `echo hello`\n2. Verify output is `hello`",
    "origin": "captured",
    "tags": ["hello", "demo"],
    "created_by": "smoke-test"
  }' | python3 -m json.tool
```

如需指定可读 slug，加上 `"record_id": "smoke-hello-001"`。

**期望**：HTTP 201，完整返回如下：

```json
{
  "id": "<UUID>",
  "name": "hello_skill",
  "description": "prints hello to the terminal",
  "body": "## Steps\n1. Run `echo hello`\n2. Verify output is `hello`",
  "version": "1.0.0",
  "origin": "captured",
  "visibility": "public",
  "level": "tool_guide",
  "tags": ["hello", "demo"],
  "input_schema": {},
  "output_schema": {},
  "created_by": "smoke-test",
  "change_summary": "",
  "content_diff": null,
  "content_fingerprint": "<sha256>",
  "parent_skill_ids": [],
  "created_at": "<timestamp>",
  "embedding": null
}
```

**判断逻辑**：
- `id` 非空 UUID — 后端自动生成的真正主键
- `name`、`description`、`body` 原样返回说明写入正常

---

## T3 — 查询 Record 列表

```bash
curl -s "$BASE/api/v1/skills/metadata?limit=10" \
  -H "Authorization: Bearer $KEY" | python3 -m json.tool
```

**期望**：`total` >= 1，`items` 里有 `smoke-hello-001`。

---

## T4 — 查询单条 Record

```bash
curl -s "$BASE/api/v1/skills/smoke-hello-001" \
  -H "Authorization: Bearer $KEY" | python3 -m json.tool
```

**期望**：返回完整 record，`body` 字段有内容。

---

## T5 — 下载 Skill（返回 Markdown 文本）

```bash
curl -s "$BASE/api/v1/skills/smoke-hello-001/download" \
  -H "Authorization: Bearer $KEY"
```

**期望**：返回纯文本，格式如下：
```
---
name: hello_skill
description: prints hello to the terminal
version: 1.0.0
tags:
  - hello
  - demo
---

## Steps
1. Run `echo hello`
...
```

**判断逻辑**：Content-Type 是 `text/markdown`，不是 ZIP。

---

## T6 — 全文搜索（含 tags）

```bash
curl -s "$BASE/api/v1/search?q=hello" \
  -H "Authorization: Bearer $KEY" | python3 -m json.tool
```

**期望**：`count` >= 1，`results` 里包含 `smoke-hello-001`，`search_type` = `"fulltext"`。

**判断逻辑**：搜索同时覆盖 `name`、`description`、`body`、`tags` 四个字段。

---

## T7 — 提交 Evolution（进化提案，纯 JSON）

```bash
EVOL_ID=$(curl -s -X POST $BASE/api/v1/evolutions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hello_skill",
    "description": "prints hello world to the terminal",
    "body": "## Steps\n1. Run `echo hello world`\n2. Verify output is `hello world`",
    "parent_skill_id": "smoke-hello-001",
    "origin": "derived",
    "change_summary": "add world to greeting",
    "tags": ["hello", "demo", "world"]
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['evolution_id'])")
echo "evolution_id: $EVOL_ID"
```

**期望**：打印出一个 UUID。

---

## T8 — 查询 Evolution 状态

```bash
curl -s "$BASE/api/v1/evolutions/$EVOL_ID" \
  -H "Authorization: Bearer $KEY" | python3 -m json.tool
```

**期望**：`status` 为 `pending` / `accepted` / `rejected` 之一，`proposed_name` = `"hello_skill"`。

---

## T9 — 手动接受 Evolution

（T8 status 仍是 pending 时执行）

```bash
curl -s -X POST "$BASE/api/v1/evolutions/$EVOL_ID/accept" \
  -H "Authorization: Bearer $KEY" | python3 -m json.tool
```

**期望**：`status` = `"accepted"`，`result_record_id` 非 null。

---

## T10 — 前端页面验证

打开浏览器分别访问两个地址，按 F12 → Console，确认无红色报错：

| URL | 检查项 |
|-----|--------|
| http://localhost:3000 | 页面正常加载，skill 列表有数据，Console 无报错 |
| http://172.26.65.21:3000 | 同上，Network 面板里 `/api/v1/skills/metadata` 返回 200 |

---

## 快速全跑脚本

```bash
#!/bin/bash
set -e
BASE="http://localhost:8000"
KEY="dev-key-for-testing"

echo "=== T1 Health ==="
curl -sf $BASE/api/v1/health | python3 -c "
import sys,json; d=json.load(sys.stdin)
assert d['status']=='ok' and d['database']=='ok', d
print('PASS')"

echo "=== T2 Register ==="
curl -sf -X POST $BASE/api/v1/skills \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"record_id":"auto-smoke-001","name":"smoke_skill","description":"automated smoke test","body":"## Steps\n1. smoke","origin":"captured","tags":["smoke"]}' \
  | python3 -c "
import sys,json; d=json.load(sys.stdin)
assert d['slug']=='auto-smoke-001', d
assert d['name']=='smoke_skill', d
assert d['body'] != '', 'body is empty!'
print('PASS name=%s slug=%s' % (d['name'], d['slug']))"

echo "=== T3 List ==="
curl -sf "$BASE/api/v1/skills/metadata?limit=5" \
  -H "Authorization: Bearer $KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['total']>=1; print('PASS total=%d' % d['total'])"

echo "=== T4 Get ==="
curl -sf "$BASE/api/v1/skills/auto-smoke-001" \
  -H "Authorization: Bearer $KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['body']!=''; print('PASS body ok')"

echo "=== T5 Download ==="
CT=$(curl -sf -I "$BASE/api/v1/skills/auto-smoke-001/download" \
  -H "Authorization: Bearer $KEY" | grep -i content-type)
echo "$CT" | grep -q "markdown" && echo "PASS content-type=markdown" || (echo "FAIL: $CT"; exit 1)

echo "=== T6 Search ==="
curl -sf "$BASE/api/v1/search?q=smoke" \
  -H "Authorization: Bearer $KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['count']>=1; print('PASS count=%d' % d['count'])"

echo ""
echo "All T1-T6 passed."
```

保存为 `/tmp/smoke.sh` 后执行：

```bash
bash /tmp/smoke.sh
```

---

## 期望结果汇总

| 测试 | 接口 | 期望状态码 | 核心断言 |
|------|------|-----------|---------|
| T1 | GET /health | 200 | status=ok, database=ok |
| T2 | POST /skills | 201 | name、description、body 原样返回 |
| T3 | GET /skills/metadata | 200 | total >= 1 |
| T4 | GET /skills/{id} | 200 | body 非空 |
| T5 | GET /skills/{id}/download | 200 | Content-Type: text/markdown |
| T6 | GET /search | 200 | count >= 1 |
| T7 | POST /evolutions | 201 | 返回 evolution_id |
| T8 | GET /evolutions/{id} | 200 | status 为合法值 |
| T9 | POST /evolutions/{id}/accept | 200 | status=accepted，result_record_id 非 null |
| T10 | 浏览器双 URL | — | Console 无红色报错 |
