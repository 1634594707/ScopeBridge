# Devpost submission draft

Status: draft for the user to edit and submit. It contains no invented user feedback, team member,
video URL or trial result. Items only the user can supply are marked **[USER]**.

## 中文版

### 项目名

**ScopeBridge（合意桥）**

### 一句话 tagline

模型可以提出理解，只有程序能定价，只有人能审核，只有客户能确认。

### Inspiration

自由职业者常见的报价摩擦不是“不会写报价单”，而是需求、预算、功能、交付日期和付款之间没有
一条可追溯的线：客户在邮件里改一句话，报价就失去依据；口头确认后，付款又对不上具体版本。
ScopeBridge 把这个过程压缩成一条可演示的主线：含糊需求 → 规则校验的方案 → 逐行报价 → 双方
确认 → PayPal 沙箱支付 → 只读订单快照。

这是一个设计假设，不是已经完成验证的市场结论。**真实用户试用尚未进行 [USER]**，提交材料不会
编造用户反馈或访谈日期。

### Text description: features and functionality

下表是可直接对照仓库验证的能力清单，不使用宣传性形容词。

| 能力 | 行为 | 证据 |
| --- | --- | --- |
| 客户归属与修订 | 客户账号拥有 brief；追加消息必须带 `expected_revision`，条件更新失败返回 409 | `backend/app/requirements/service.py#L170-L255`；`backend/tests/test_api_quote_flow.py` |
| 规则定价与可行性 | 页数、附加项、预算、截止日期、素材、能力由纯函数判断；三页 = 70000 分，50000 预算不通过 | `backend/app/rules/pricing.py`；`backend/app/rules/feasibility.py`；`backend/tests/test_pricing.py`、`test_feasibility.py` |
| 模型事实抽取 | 只接受五个键 `pages/budget_usd/deadline_days/assets_ready/features`，`extra="forbid"`，金额不进入报价 | `backend/app/ai/schemas.py#L17-L28`；`prompts.py#L22-L43`；`tests/test_ai_extraction.py` |
| 方案与报价版本 | 每修订最多两个方案；报价行带 `rule_ref` 和来源消息；新修订使 `DRAFT/REVIEWED/CONFIRMED` 失效 | `backend/app/proposals/service.py`；`backend/app/quotes/service.py#L26-L166`；`frontend/src/components/QuoteDiff.tsx` |
| 双方身份与确认 | 工作室/客户分别登录、CSRF、所有权检查；客户确认精确版本 | `backend/app/api/deps.py#L54-L93`；`backend/app/accounts/service.py`；`frontend/src/pages/PortalPage.tsx` |
| PayPal 沙箱支付 | Orders v2 create → approve → capture → query；金额来自已确认报价；未知结果进 `RECONCILING` | `backend/app/payments/service.py#L77-L182`、`#L397-L451`；`backend/app/paypal/client.py#L137-L208` |
| 快照与已支付终态 | 验证后的 capture 与 `PAID`、`CLOSED`、不可变快照同一事务；已支付 brief 拒绝新工作 | `backend/app/payments/service.py#L694-L839`；`backend/app/payments/models.py#L74-L93`；`backend/app/requirements/service.py#L27-L145` |
| 无凭据降级 | 无模型 key 返回 503 `model_not_configured`；无 PayPal 凭据返回 503 `paypal_not_configured` 且不锁报价 | `backend/app/ai/service.py#L41-L48`；`backend/app/payments/service.py#L67-L75`；`README.md` 的 “Running without credentials” |

### How we built it

- 前端：React + TypeScript + Vite + Tailwind CSS。
- 后端：Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL。
- 外部：OpenAI-compatible 模型（事实抽取）、PayPal Orders v2 沙箱（create/approve/capture/query）。
- 运行：Docker Compose PostgreSQL；`scripts/verify.ps1` / `scripts/verify.sh` 从隔离数据库到
  `pytest`、`ruff`、`tsc`、`vite build` 一键验证。
- 测试：109 个后端测试（本次实测 `109 passed`）；19 个规则级评测案例，报告在
  `evals/reports/`。

### Tools（可直接粘贴）

AI 使用 OpenAI-compatible 聊天补全接口（`POST {MODEL_BASE_URL}/chat/completions`，temperature 0，`response_format=json_object`，prompt `facts-v7`）。它只把客户 brief 读成五个事实：`pages`、`budget_usd`、`deadline_days`、`assets_ready`、`features`；任何金额都不进入报价。当前运行的供应商与模型名由 `.env` 的 `MODEL_NAME` 提供，仓库不硬编码；2026-10-30 的评测报告记录了一次 `deepseek-v4.1-flash` 运行。PayPal 侧使用 Orders v2 沙箱：OAuth2 token、create order（intent CAPTURE）、capture、get order；金额从服务端已确认报价读取。

### Challenges

- **模型输出不稳定**：这个网关不投递 system message，且会返回 markdown/额外键。解决方案是把契约
  同时放进 user payload，`extra="forbid"` 整包拒绝，失败也写入 `ai_extractions`。
- **支付状态未知**：capture 可能超时、响应可能丢失；不能把“浏览器回来了”当支付成功。解决方案是
  先锁报价、再调用外部、未知结果进 `RECONCILING`，只由 PayPal 查询/verified capture 写入 PAID。
- **双向身份与版本**：工作室和客户都登录，brief 归客户所有；brief 修订会让旧报价失效，支付锁定
  期间不允许改版本。
- **并发与幂等**：`expected_revision` 条件更新、唯一 `Idempotency-Key`、同一 `PayPal-Request-Id`
  重试、部分唯一索引保证每报价最多一个活跃 attempt。

### Accomplishments

- 规则定价与可行性是零 IO 的纯函数；三页 = 70000 分，50000 预算不通过，这一条有测试。
- 模型只给事实，服务端构建最多两个方案；模型金额不会进入报价。
- 一次真实 PayPal 沙箱 capture 的记录在 demo 数据库：order `5UL759133K5843017`、capture
  `5AR676939L8640110`、$500.00；本地只读查询已核实。视频必须由用户重新录制，不能把这条记录说成
  视频结果。
- 19 例评测：pipeline 解析 19/19，6 个原需求可满足、6 个收窄方案、7 个诚实“无解”；baseline
  解析 18/19，2 个被规则拒绝的声明。报告路径与运行日期写在 README，单次运行，不外推为“模型准确率”。
- 109 个后端测试通过；`ruff`、`tsc -b`、`vite build` 通过；隔离环境脚本实测 30.4 秒（含
  `uv sync`/`pnpm install` 的最新一次；更早的 cold run 为 40.8 秒）。

### What we learned

- 价格必须由规则层产生；模型可以理解文本，但不能成为金额的来源。
- “未知”必须是一等状态，不能为了方便把它归成成功或失败。
- 可审计的记录比“看起来智能”更重要：每条报价要能追到规则和客户原话，支付要能追到订单/快照。
- 演示路径必须和代码状态一致；不能写一个 UI 不存在的按钮。

### What's next

- 真实用户试用与访谈记录（当前未做）。
- 视频与 Devpost 提交材料（当前未完成）。
- 生产级 PayPal 集成：webhook、定时对账、退款/部分 capture。
- 多服务商/多币种；更完整的报价配置。
- 浏览器 E2E（Playwright 当前未实现，材料中不声称已实现）。

### 未实现/未声称

- Playwright/E2E：未实现，浏览器流程为手工脚本。
- 真实用户试用：未做。
- M6 视频：未录制；视频 URL 由用户提供。
- PayPal 生产环境、退款、部分 capture、无人值守对账：不在本版本范围。

---

## English version (submission copy)

### Project name

**ScopeBridge**

### Tagline

The model may propose; only a program prices; only a human reviews; only the client confirms.

### Inspiration

Freelancers lose time and trust in the gap between a vague request, a budget, a delivery date and a
payment. A single email change can detach a quote from its basis, and a verbal yes cannot be matched
to the exact version that was paid. ScopeBridge turns that gap into one observable line: ambiguous
brief → rule-checked options → line-item quote → two-sided confirmation → PayPal sandbox payment →
read-only order snapshot.

This is a design hypothesis, not a validated market claim. **A real user trial has not been run
[USER]**; the submission must not invent feedback or interview dates.

### Text description: features and functionality

Each row is verifiable against the repository; this is not marketing copy.

| Feature | Behaviour | Evidence |
| --- | --- | --- |
| Client-owned brief and revision CAS | The client account owns the brief; appends require `expected_revision` and return 409 on a stale write | `backend/app/requirements/service.py#L170-L255`; `backend/tests/test_api_quote_flow.py` |
| Rule pricing and feasibility | Pages, add-ons, budget, deadline, assets and capabilities are judged by pure functions; three pages = 70000 cents and a 50000 budget fails | `backend/app/rules/pricing.py`; `backend/app/rules/feasibility.py`; `backend/tests/test_pricing.py`, `test_feasibility.py` |
| Model fact extraction | Only five keys are accepted (`pages/budget_usd/deadline_days/assets_ready/features`), `extra="forbid"`; model money never reaches a quote | `backend/app/ai/schemas.py#L17-L28`; `prompts.py#L22-L43`; `tests/test_ai_extraction.py` |
| Options and quote versions | At most two options per revision; quote lines carry `rule_ref` and source messages; a revision supersedes `DRAFT/REVIEWED/CONFIRMED` | `backend/app/proposals/service.py`; `backend/app/quotes/service.py#L26-L166`; `frontend/src/components/QuoteDiff.tsx` |
| Two seats and confirmation | Studio/client sign-in, CSRF and ownership checks; the client confirms the exact version | `backend/app/api/deps.py#L54-L93`; `backend/app/accounts/service.py`; `frontend/src/pages/PortalPage.tsx` |
| PayPal sandbox payment | Orders v2 create → approve → capture → query; amount comes from the confirmed quote; unknown results enter `RECONCILING` | `backend/app/payments/service.py#L77-L182`, `#L397-L451`; `backend/app/paypal/client.py#L137-L208` |
| Snapshot and paid terminal state | Verified capture, `PAID`, `CLOSED` and the immutable snapshot share one transaction; a paid brief rejects new work | `backend/app/payments/service.py#L694-L839`; `backend/app/payments/models.py#L74-L93`; `backend/app/requirements/service.py#L27-L145` |
| No-credential degradation | No model key returns 503 `model_not_configured`; no PayPal credentials returns 503 `paypal_not_configured` without locking the quote | `backend/app/ai/service.py#L41-L48`; `backend/app/payments/service.py#L67-L75`; “Running without credentials” in `README.md` |

### How we built it

- Frontend: React + TypeScript + Vite + Tailwind CSS.
- Backend: Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL.
- External: an OpenAI-compatible model for fact extraction; PayPal Orders v2 sandbox for
  create/approve/capture/query.
- Runtime: PostgreSQL in Docker Compose; `scripts/verify.ps1` / `scripts/verify.sh` run an isolated
  database, migrations, seed, `pytest`, `ruff`, `tsc -b` and `vite build` in one command.
- Tests: 109 backend tests (actual run: `109 passed`); 19 rule-level evaluation cases with reports in
  `evals/reports/`.

### Tools (submission copy)

AI: an OpenAI-compatible chat-completions endpoint (`POST {MODEL_BASE_URL}/chat/completions`, temperature 0, `response_format=json_object`, prompt `facts-v7`). It only extracts five facts from the brief — `pages`, `budget_usd`, `deadline_days`, `assets_ready`, `features` — and never supplies a quote amount. The running provider/model name is supplied by `MODEL_NAME` in `.env` and is not hard-coded; a recorded 2026-10-30 evaluation used `deepseek-v4.1-flash`. PayPal: Orders v2 sandbox via OAuth2 token, create order (intent CAPTURE), capture, and get order; the amount is read from the server-side confirmed quote.

### Challenges

- **Unstable model output**: this gateway did not deliver the system message and returned markdown or
  extra keys. The contract travels with the user payload, `extra="forbid"` rejects the whole answer,
  and every attempt is stored in `ai_extractions`.
- **Unknown payment state**: a capture can time out or lose its response; a browser return is not
  proof. The server locks the quote first, calls PayPal second, parks unknown results in
  `RECONCILING`, and only a verified capture writes `PAID`.
- **Two-sided identity and versions**: both seats sign in; briefs belong to the client; revisions
  supersede old quotes; payment locks prevent edits while an external result is unknown.
- **Concurrency and idempotency**: a conditional `expected_revision` update, a unique
  `Idempotency-Key`, the same `PayPal-Request-Id` on retry, and a partial unique index for one active
  attempt per quote.

### Accomplishments

- Pricing and feasibility are zero-IO pure functions; three pages = 70000 cents, and a 50000 budget
  fails. This is covered by tests.
- The model returns facts only; the server builds at most two options and prices them. Model money
  never becomes a quote amount.
- One real PayPal sandbox capture is recorded in the demo database: order `5UL759133K5843017`,
  capture `5AR676939L8640110`, $500.00. It was verified with a local read-only query; the video must
  be recorded separately and must not present that database record as a video result.
- 19-case evaluation: the pipeline parsed 19/19 and produced 6 original-fit options, 6 narrowed
  options and 7 honest "no solution" answers; the baseline parsed 18/19 and made 2 claims the rules
  reject. The report path and run date are in the README; it is a single run and is not extrapolated
  to "model accuracy".
- 109 backend tests pass; `ruff`, `tsc -b` and `vite build` pass; the isolated verification script
  finished in 30.4 seconds on the latest run (including `uv sync`/`pnpm install`; an earlier cold
  run was 40.8 seconds).

### What we learned

- Prices must come from the rules layer; a model can read text but must not be the source of money.
- "Unknown" needs to be a first-class state, not a convenient success or failure.
- Auditability matters more than the appearance of intelligence: every quote line traces to a rule
  and a client message; every payment traces to an order and a snapshot.
- A demo path must match the code state; never script a button the UI does not have.

### What's next

- Run and record a real user trial.
- Finish the demo video and Devpost submission materials.
- Production PayPal integration: webhooks, scheduled reconciliation, refunds and partial captures.
- Multi-provider/multi-currency support and richer rule configuration.
- Browser E2E; Playwright is not implemented in this build and is not claimed as implemented.

### Not implemented / not claimed

- Playwright/E2E: not implemented; the browser flow is a manual script.
- Real user trial: not run.
- M6 video: not recorded; the video URL is supplied by the user.
- Production PayPal, refunds, partial captures and unattended reconciliation are out of scope.

---

## Required items and ownership

| Item | Status | Who |
| --- | --- | --- |
| Commit and push the current worktree | The 2026-11-02 compliance/verification/Path B changes are uncommitted; a public judge cannot see them until pushed | **[USER]** |
| Public code repository URL | Repository exists at `https://github.com/1634594707/ScopeBridge` (remote); confirm it is public | **[USER]** |
| License visible in the GitHub About area | MIT `LICENSE` is in the repo root; About visibility must be confirmed on GitHub | **[USER]** |
| Demo video URL (≤3 minutes) | Not recorded; use `docs/DEMO_SCRIPT.md` | **[USER]** |
| Real trial feedback / interview record | Not run; do not invent | **[USER]** |
| Team information | Not recorded in the repo | **[USER]** |
| Devpost text fields | This draft is the starting copy | **[USER]** edit and submit |
| Tech tags | React, TypeScript, Vite, Tailwind CSS, Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Docker, PayPal Orders v2, OpenAI-compatible model | ready to select |
| Screenshot numbers | See mapping below | ready |
| Sandbox account / run instructions | `README.md`, `docs/M6_RUNBOOK.md` | ready |
| Clean verification evidence | `scripts/verify.ps1` / `.sh`; last run in `docs/M6_RUNBOOK.md` | ready |

### Screenshot mapping

- `01-landing.png` — landing / product promise
- `02-seller-console.png` — seller desk
- `03-requirement-workspace.png` — brief + scope editor
- `04-quote-confirmed.png` — confirmed quote
- `05-client-portal.png` — client portal
- `06-client-portal-mobile.png` — mobile portal
- `07-model-draft.png` — model facts
- `08-model-options.png` — server-priced options
- `09-payment-panel.png` — payment card
- `10-payment-history.png` — recorded sandbox payment history
- `11-quote-diff.png` — version diff
- `12-payment-review.png` — payment review
- `13-payment-confirmed.png` — PayPal return confirmed
- `14-order-snapshot-client.png` / `15-order-snapshot-seller.png` — frozen snapshot
- `16-payment-verifying.png` — `RECONCILING` (UI label “Verifying”)
- `17-payment-retry-recovered.png` — retry recovered
- `18-payment-awaiting.png` — awaiting approval
- `19-scope-estimator.png` — public estimator
- `20-client-briefs.png` — client brief list / Closed filter
- `21-payment-attention.png` — seller attention
- `22-sign-in.png` — two seats
- `23-start-brief.png` — client intake
- `24-payment-close.png` — manual close, unlock

Screenshots 10 and 13–15 are the demo database's recorded sandbox capture; the others are from an
isolated demo dataset. The submission must not claim that every screenshot is a live production
payment.
