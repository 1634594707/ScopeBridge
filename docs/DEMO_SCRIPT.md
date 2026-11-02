# Demo script — 3 minutes, two paths

Two recordings, both under three minutes. Path A is the sale that works; Path B is the payment
whose create result is unknown. Record them separately so a single mistake does not cost the whole
take. This file is a shooting script, not a record of a finished video.

Numbers below are the real values from the seeded demo, not placeholders.

## Before recording

### Services and data

- Demo database: `docker compose ps` shows `scopebridge-db` healthy. Do not run `down -v`; the
  database holds the recorded sandbox snapshot (`5UL759133K5843017` / `5AR676939L8640110` / $500.00).
- API: `GET http://127.0.0.1:8000/api/health` returns `200 {"status":"ok"}`.
- Frontend: `pnpm exec vite preview` on `http://127.0.0.1:4173`; `APP_BASE_URL` must be exactly
  `http://127.0.0.1:4173` so PayPal returns to the right page.
- Path A uses the normal `.env` `DATABASE_URL` (the demo database). Path B uses the isolated
  `scopebridge_pathb` database; run `scripts/prepare-demo-pathb.ps1` first (see
  `docs/M6_RUNBOOK.md`).
- Do not re-seed the demo database after Path A. The snapshot is the evidence.

### Accounts and credentials

- Studio: `SELLER_EMAIL` / `SELLER_PASSWORD` from `.env`.
- Client: `CLIENT_EMAIL` / `CLIENT_PASSWORD` from `.env`.
- PayPal sandbox buyer: the Personal sandbox account from developer.paypal.com; do not show email
  or password on screen.
- PayPal API: `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` in `.env`; sandbox only.
- Model: `MODEL_API_KEY` / `MODEL_NAME` optional. If absent, skip the model draft and use the scope
  editor directly; the paid path still works.

### Browser and capture

- Window 1440×900, browser zoom 100%, bookmarks bar hidden.
- Disable notifications, close unrelated tabs, hide the desktop/taskbar if possible.
- Sign out of any existing session before the take. The client and studio seats use different
  sessions; switch by signing out and signing in again.
- English captions are burned in; spoken language may be Chinese.

### Prewarm pages (before pressing record)

Open these once and wait for them to finish loading:

- `/`, `/signin`, `/start`, `/briefs`, `/console`, `/rules`
- Path A brief and quote pages used in the take
- Path B brief and payment page used in the take

This avoids first-load spinners and model/API stalls on camera.

### Failure-injection switch (Path B only)

Use a process environment variable; do not edit `.env`:

```powershell
# terminal 1: start Path B API with a tiny create timeout
$line = Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$env:DATABASE_URL = ($line -replace '/scopebridge', '/scopebridge_pathb')
$env:PAYPAL_TIMEOUT_SECONDS = "0.05"
cd backend
uv run uvicorn app.main:app --port 8000
```

Restart order when restoring:

1. Stop the API with `Ctrl+C`.
2. Set `$env:PAYPAL_TIMEOUT_SECONDS = "30"` in the same terminal.
3. Start the API again.
4. Wait for `/api/health`.
5. Return to the seller console and press **Retry create**.

The settings are read at process start, so a restart is required. Do not use `PAYPAL_TIMEOUT_SECONDS`
in Path A; leave it unset/30 there.

---

## Path A — brief to paid (2:40)

| Time | Screen | Action | Chinese narration | Burned-in English subtitle |
| --- | --- | --- | --- | --- |
| 0:00–0:08 | `/` | Land on the home page; show the headline and specimen card | 自由职业者最怕的不是写代码，是需求没对齐就开工。 | "Freelancers lose money in the gap between a vague request and a signed scope." |
| 0:08–0:15 | `/` | Hover the specimen card; do not scroll | 这里把需求、价格和确认连成一条线。 | "One line from a vague request to a paid, confirmed scope." |
| 0:15–0:25 | `/signin` | Sign in as the demo client | 客户也有账号，每个动作都能追溯到人。 | "The client has an account too — every action is attributable to a sign-in." |
| 0:25–0:40 | `/start` | Submit the coffee-shop brief: budget 500, three weeks, no assets | 客户还是按写邮件的方式说需求；预算、日期和素材是结构化字段。 | "They write it like an email; budget, deadline and assets are explicit fields." |
| 0:40–0:48 | `/signin` | Sign out of the client seat; sign in as the studio | 现在切到工作室座位。 | "Switch to the studio seat." |
| 0:48–1:05 | `/console` → brief | Open the brief; press **Draft with the model**; wait for facts and two options | 模型只读事实：页数、预算、截止日期、素材和功能；它不报价。 | "The model reads five facts — it never sets a price." |
| 1:05–1:18 | same | Point at "As briefed $700 / cannot deliver" then "One-page launch $500 / deliverable" | 服务端用规则给两个方案定价；超预算的方案不藏起来。 | "The server prices both options. The over-budget one stays visible with its exact violation." |
| 1:18–1:32 | same | **Use this scope** → **Price this scope** → **Draft quote** | 工作室采用收窄后的方案，生成逐行报价。 | "The studio adopts the narrowed scope and issues a quote line by line." |
| 1:32–1:45 | `/quotes/:id` | Scroll line items; open the rule sidebar; press **Review and issue** | 每一行都能追到规则和客户原话。 | "Every amount points at the rule that priced it and the message that justified it." |
| 1:45–1:55 | `/signin` | Sign out of the studio; sign in as the client | 切回客户座位。 | "Back to the client seat." |
| 1:55–2:05 | `/briefs/:id` | Open the brief from **My briefs**; pick the scope; press **Confirm this version** | 客户确认的是这一个精确版本。 | "The client confirms one exact version." |
| 2:05–2:15 | `/briefs/:id` | Press **Continue to PayPal**; read the payment card | 金额从服务端的已确认报价读取，客户不发送金额。 | "The amount is read from the confirmed quote on the server." |
| 2:15–2:32 | PayPal sandbox → `/pay/:id` | Approve as the sandbox buyer; the return page captures automatically | 从 PayPal 回来不等于已支付；服务器会先向 PayPal 确认 capture。 | "Returning is not proof — the server confirms the capture with PayPal." |
| 2:32–2:40 | `/pay/:id` | Show order/capture/payer, then **Back to your brief** | 金额、订单和付款人被冻结成只读快照。 | "Amount, order and payer are frozen into one read-only snapshot." |

If the model credentials are not configured, skip **Draft with the model** and use the scope editor
directly: one page, external order link, assets still pending. The server still prices it; the model
step is advisory, not required for the paid path.

---

## Path B — the payment that never returned an order id (1:30)

Use the isolated Path B database and the prefilled confirmed quote. Start the API with
`PAYPAL_TIMEOUT_SECONDS=0.05` as shown above, and confirm the quote is `CONFIRMED` before recording.

| Time | Screen | Action | Chinese narration | Burned-in English subtitle |
| --- | --- | --- | --- | --- |
| 0:00–0:08 | `/console` → brief | Open the second brief; show the quote is `CONFIRMED` | 同样的流程，但这次 PayPal 创建订单没有及时回应。 | "Same flow, but this time PayPal never answered in time." |
| 0:08–0:20 | `/briefs/:id` | Sign in as the client if needed; open the brief; press **Continue to PayPal** | 客户发起支付。 | "The client starts the payment." |
| 0:20–0:30 | seller `/console` → brief → Payments | Show `RECONCILING`, `order pending`, `create_unknown`; quote is locked | 结果未知，所以停在“验证中”，不猜成功也不猜失败。 | "The attempt is parked, not guessed. The quote stays locked." |
| 0:30–0:40 | terminal / title card | Stop the API; set `PAYPAL_TIMEOUT_SECONDS=30`; restart; wait for health | 恢复超时设置并重启 API，然后让服务器去查询原订单。 | "Restore the timeout, restart the server, then verify." |
| 0:40–0:55 | seller Payments | Press **Retry create**; the order id appears; status returns to `AWAITING_APPROVAL` | 同一个 request id 重试：PayPal 返回它可能已经创建的订单。 | "One retry with the same request id: PayPal returns the order it may already have made." |
| 0:55–1:05 | `/pay/:id` | Open the payment status; press the PayPal approval link | 只有买家能批准。 | "Only the buyer can approve the order." |
| 1:05–1:20 | PayPal sandbox → `/pay/:id` | Approve; the return page captures and shows `COMPLETED` | 服务器确认 capture 后才写快照。 | "The server verifies the capture before it writes the snapshot." |
| 1:20–1:30 | `/briefs/:id` | Show quote `PAID` and brief `CLOSED` | 恢复路径记录了同一笔订单；报价和 brief 变成只读。 | "The recovery records the same order; the quote and brief become read-only." |

Path C (optional, do not mix into the same take): keep `PAYPAL_TIMEOUT_SECONDS` low, press **Retry
create** twice; when both retries still return no order id, press **Close**, write what you checked
in PayPal, and the quote returns to `CONFIRMED`. A retry success and a manual Close are separate
outcomes.

### What not to do in Path B

- Do not press **Close** after a successful **Retry create**. The retry success is
  `AWAITING_APPROVAL`; Close is only for `RECONCILING`/`FAILED`.
- Do not edit `.env` for the timeout switch; use the process environment and restart.
- Do not show the PayPage and the seller console claiming different states without a refresh.

---

## Single ≤3:00 submission cut

The two paths above are shooting scripts; the submission video must be one take under 3:00. Use this
cut instead of concatenating 2:40 + 1:30 (which would be 4:10).

| Time | Content | Action | Subtitle |
| --- | --- | --- | --- |
| 0:00–0:10 | Pitch | Landing headline + one sentence | "A vague brief becomes a priced, confirmed scope." |
| 0:10–0:25 | Client brief | Sign in as client; submit the coffee-shop brief | "Budget, deadline and assets are explicit fields." |
| 0:25–0:38 | AI facts | Cut to studio; press Draft with the model; show five facts and two options | "The model extracts facts; the server prices them." |
| 0:38–0:52 | Scope + quote | Use the narrowed scope; price; draft quote | "The over-budget option stays visible." |
| 0:52–1:02 | Review | Quote page; review and issue | "Every line traces to a rule and a client message." |
| 1:02–1:15 | Client confirm | Cut to client; confirm the exact version | "The client confirms one exact version." |
| 1:15–1:32 | PayPal | Approve; return page captures | "Returning is not proof; the server verifies the capture." |
| 1:32–1:40 | Snapshot | Show order/capture/payer; brief `CLOSED` | "The paid lines are a read-only snapshot." |
| 1:40–2:15 | Recovery | Cut to Path B: show `RECONCILING`; retry; order id; `COMPLETED` | "Unknown is a state; retry uses the same request id." |
| 2:15–2:25 | Close/end | End card with repo/run instructions; subtitle about manual Close | "The manual-close path is documented; no third-party claims." |

Cut from the submission video: landing hover/scroll, full sign-in transitions (use quick cuts), model
latency (cut after facts appear), long quote scrolling, the Path C close take. Explain the cuts with
subtitles: “two seats, sign out to switch”, “Path C: manual close after a PayPal check is documented,
not shown”. The video must show the app actually running; do not use a design mockup.

## Recording notes

- The video is under three minutes per path; judges are not required to watch beyond three.
- Start the API and `vite preview` before recording.
- Path A uses the demo database. Path B uses `scopebridge_pathb`; switch the API's `DATABASE_URL`
  and restart before Path B.
- The model draft is optional and advisory. If no model credentials, use the manual scope editor.
- The PayPal sandbox buyer must approve by hand; no card details are entered into the app.
- The recorded sandbox snapshot is existing evidence; do not re-seed or delete the demo volume.

## Talking points for the Devpost text (not spoken)

- PayPal Orders v2 is used for real: create → approve → capture, plus query for recovery.
- The amount is always read from the confirmed quote on the server; the client sends no payment
  amount.
- The model returns facts only; the server builds and prices options. The evaluation report compares
  that against one-shot model quoting.
- 19 fixed cases, one run each (reported with denominator): pipeline parsed 19/19 and produced
  6 original-fit options, 6 narrowed options and 7 honest "no solution" answers; the one-shot
  baseline parsed 18/19 and made 2 claims the rules reject.
- Known limits: sandbox only, no webhooks, recovery is seller-triggered, no refunds, no Playwright.
