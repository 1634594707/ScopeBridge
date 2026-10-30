# ScopeBridge 开发记录

**本文记录当前实现，随代码更新。** 规划与验收标准在 `FORMAL_PROPOSAL.md`（v3.0）；开工前的旧基线已归档到
`archive/PROJECT_PLAN-v2.md`；给评委的英文入口是根 `README.md`。

## 里程碑状态

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| M0 | 脚手架：uv + FastAPI + SQLAlchemy/Alembic、Vite/React/Tailwind、Docker PostgreSQL、健康检查 | 完成 |
| M1 | 纯函数定价与可行性验证器 + 五个固定案例 | 完成 |
| M2 | 需求/方案/报价/审核/确认，权限与版本冲突 | 完成 |
| M3 | 模型接入：只抽事实，服务端生成并定价候选方案 | 完成 |
| M4 | PayPal 沙箱创建、批准、捕获与恢复 | 完成（真实沙箱已跑通一笔 $500） |
| M5 | 版本差异、结构化改需求、19 案例双链路评测 | 完成（真实用户试用未做） |
| M6 | 干净环境复现、演示视频、提交材料 | 待办 |

## 目录与模块

```
backend/app/
  core/           配置、数据库会话、统一错误体、口令哈希
  accounts/       卖家会话、登录限流、CSRF
  service_rules/  不可变服务规则版本
  requirements/   需求与修订消息（expected_revision CAS）
  proposals/      候选方案（程序定价与裁决，每修订最多两个）
  quotes/         报价版本、行项、状态机
  payments/       支付尝试、核验、恢复、订单快照
  paypal/         Orders v2 适配器（唯一发出外部 HTTP 的地方）
  ai/             模型客户端、提示词、事实校验、候选构造
  rules/          纯函数定价与可行性，零 IO
frontend/src/     pages/、components/、lib/{api,types,format}
evals/            cases.json、run_eval.py、metrics.py、reports/
```

## 环境变量

`.env`（不入库）至少包含：`DATABASE_URL`、`SESSION_SECRET`、`SELLER_PASSWORD`、`MODEL_BASE_URL`、
`MODEL_API_KEY`、`MODEL_NAME`、`PAYPAL_CLIENT_ID`、`PAYPAL_CLIENT_SECRET`、`PAYPAL_BASE_URL`、
`APP_BASE_URL`。可选：`PAYPAL_MERCHANT_ID`、`PAYPAL_TIMEOUT_SECONDS`、`ARGON2_MEMORY_COST`。

`APP_BASE_URL` 必须与浏览器实际打开的地址一致（预览 4173 / 开发 5173）：PayPal 会把买家送回
`{APP_BASE_URL}/pay/{attempt_id}`。

## 数据模型（实际）

| 表 | 要点 |
| --- | --- |
| `service_rule_versions` | 不可变规则 JSON：基础页价、加页价、加项目录、能力列表、排除项、交期 |
| `requirements` / `requirement_messages` | 单需求一条 portal token（仅存哈希）；消息带预算、交期、素材状态、修订号 |
| `proposals` | 方案与规则版本绑定，含包含项、排除项、校验结果 |
| `quote_versions` / `quote_items` | 版本号、行项、`rule_ref`、来源消息、审核与确认时间、状态 |
| `payment_attempts` | 幂等键、PayPal order/capture id、状态、`retry_count`、人工结案人与依据 |
| `order_snapshots` | 每笔成功支付唯一；与 `PAID` 同一事务写入，之后不可改 |
| `ai_extractions` | 每次模型调用：模型名、提示词版本、输入消息 id、原始输出、解析结果、错误码、耗时 |

## API（当前实现）

| 方法与路径 | 权限 |
| --- | --- |
| `POST/GET/DELETE /api/session` | 卖家 |
| `GET /api/service-rules` | 公开 |
| `POST /api/requirements` | 公开（一次性返回 portal token） |
| `GET /api/requirements`、`GET /api/requirements/{id}` | 卖家 |
| `POST /api/requirements/{id}/messages` | 卖家（CSRF） |
| `POST /api/requirements/{id}/proposals` | 卖家（CSRF） |
| `POST /api/requirements/{id}/extractions`、`GET .../latest` | 卖家（CSRF） |
| `POST /api/requirements/{id}/quotes` | 卖家（CSRF） |
| `POST /api/quotes/{id}/review` | 卖家（CSRF） |
| `GET /api/portal`、`POST /api/portal/messages` | 客户令牌 |
| `POST /api/portal/proposals/{id}/select` | 客户令牌 |
| `POST /api/portal/quotes/{id}/confirm` | 客户令牌 |
| `POST /api/portal/quotes/{id}/payment-attempts` | 客户令牌 + `Idempotency-Key` |
| `GET /api/portal/payments/{id}`、`POST .../capture` | 客户令牌 |
| `POST /api/payments/{id}/reconcile` / `/retry-create` / `/close` | 卖家（CSRF） |
| `GET /api/requirements/{id}/payments`、`/order` | 卖家 |
| `GET /api/orders/{id}` | 卖家 |
| `GET /api/health` | 公开 |

错误体统一为 `{code, message, details?}`；写操作带 `Idempotency-Key` 与 `expected_revision`，冲突返回 `409`。

## 状态机与恢复

- 报价：`DRAFT → REVIEWED → CONFIRMED → PAYMENT_LOCKED → PAID`，修订变更使草稿 `SUPERSEDED`。
  解锁只有两条路径：服务端核验出「确定未成功捕获」，或卖家核对 PayPal 后人工结案。
- 支付：`CREATING → AWAITING_APPROVAL → CAPTURING → COMPLETED`；结果不明进入 `RECONCILING`；
  确定失败进入 `FAILED`；人工结案进入 `ABANDONED`。
- 创建无回执：同 `PayPal-Request-Id` 重试，最多 2 次；仍失败则人工结案（需勾选已核对 + ≥10 字依据，
  记录结案人与时间）。
- 捕获响应丢失：查询原订单，`COMPLETED` 补写快照，`APPROVED` 恢复捕获，`VOIDED/EXPIRED` 判失败。

## 模型契约

- 提示词版本：`facts-v7`。模型只返回五个键：`pages`、`budget_usd`、`deadline_days`、`assets_ready`、
  `features`；`extra="forbid"`，散文、代码围栏、多余键一律 `422`。
- **契约必须随用户消息一起发送**：实测该网关不传达 system 消息，模型只看到简报就会自造 schema。
  改提示词措辞无效，改通道才有效（解析率 47% → 100%）。
- 候选方案由 `app/ai/candidates.py` 构造，`app/rules` 定价；模型的金额一律丢弃。

## 评测

19 个规则级案例（`evals/cases.json`）+ 1 个流程级案例（由接口测试覆盖）。`evals/metrics.py` 定义口径：
所有比例以「调用次数」为分母，管线的不安全放行由运行期重新复算得到，不做硬编码。

```bash
cd backend
uv run python ../evals/run_eval.py --runs 1 --workers 1 --timeout 90 --pause 1 --tag <label>
```

报告落在 `evals/reports/<时间戳>[-<tag>].{json,md}`。

## 与初版计划的偏差

| 计划 | 实际 | 原因 |
| --- | --- | --- |
| 模型输出候选方案 + 依据 | 模型只出事实，服务端构造候选 | 嵌套输出在该网关上不稳定；组合判断本质是规则问题 |
| 支付端点挂在 `/api/quotes/{id}/payment-attempts` | 挂在 `/api/portal/quotes/{id}/payment-attempts` | 发起者是客户，权限路径必须与客户身份一致 |
| 客户端提交金额 | 请求体无金额字段 | 金额唯一来源是规则层 |
| 评测每例 3 次 | 已记录为 1 次全量 | 网关超时导致多次尝试中断；报告已标注，未以多次结果充数 |

## 提交前的验证命令

```bash
cd backend && uv run pytest -q && uv run ruff check .
cd frontend && pnpm exec tsc -b && pnpm exec vite build
npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
```
