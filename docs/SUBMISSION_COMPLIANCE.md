# Submission compliance table

Status date: 2026-11-02. This file checks the repository against the hackathon submission requirements.
Every “satisfied” claim below has a repository-referenced evidence; anything without evidence is
marked “not locally verifiable” and is not treated as passed.

## Hard-gap conclusion first

1. **Functional demo: choose A (judges run from the repo).** A judge can clone, start PostgreSQL,
   migrate, seed and open the UI without model or PayPal credentials. They can sign in, submit a
   brief, price a scope manually, issue/review a quote and confirm it. The model draft and PayPal
   payment stop with explicit 503 errors; a real sandbox payment needs the judge to supply sandbox
   credentials. B (hosted demo) is not deployed and is optional; the minimum deployment steps are
   listed below. A is the honest submission path.
2. **AI load-bearing: partially satisfied / risk.** The model is used to extract facts and build
   scope options, but `POST /api/extractions` is optional and `create_quote` does not require an
   extraction; the manual scope editor can complete the whole quote/confirm flow without the model.
   Under “AI must be meaningfully integrated”, this is a real bypass risk. The smallest fixes are a
   model-derived clarification gate and an AI change summary; they are proposed below, not coded.
3. **Video: use one ≤3:00 cut, not two videos.** Do not concatenate Path A (2:40) and Path B (1:30),
   which is 4:10. `docs/DEMO_SCRIPT.md` now contains a 2:25 single cut: keep brief → facts → options
   → quote → confirm → PayPal → snapshot, plus a 35-second recovery segment; cut landing motion,
   full sign-in transitions, model latency, long quote scrolling and Path C close. Explain the cuts
   with subtitles. No recorded result is claimed here.

## Rubric mapping

| Requirement | Status | Evidence | Gap / action | Owner |
| --- | --- | --- | --- | --- |
| Project built with organizer developer tools | **Satisfied** | PayPal Orders v2 integration in `backend/app/paypal/client.py#L137-L208`; AI client in `backend/app/ai/client.py#L29-L60` | None in repo; ensure the Devpost form names both | Repo / user |
| Every project must meaningfully use PayPal | **Satisfied** | Payment is the closing step: quote lock, create, approve, capture, query, amount verification, snapshot in `backend/app/payments/service.py#L77-L182`, `#L394-L451`, `#L694-L839`; sandbox capture recorded in the demo DB (`5UL759133K5843017` / `5AR676939L8640110` / 50000) | No webhooks/refunds; sandbox only. Not a reason to call it incomplete. | Repo / user |
| PayPal integration is central | **Satisfied** | The quote cannot become `PAID` without a verified PayPal capture; `_finalize` writes `PAID` + `CLOSED` + snapshot in one transaction; amount comes from the quote, not the client. See `backend/app/payments/service.py#L694-L839`; API `backend/app/paypal/client.py#L137-L208` | The demo can stop before PayPal without credentials; that does not remove the integration from the product | Repo / user |
| AI is meaningfully used | **Partial / risk** | Facts-only model: `backend/app/ai/prompts.py#L22-L43`, `backend/app/ai/schemas.py#L17-L28`, `backend/app/ai/client.py#L29-L60`; options built by `backend/app/ai/candidates.py`; evidence rows `ai_extractions` | `POST /api/extractions` is optional; `create_quote` has no extraction check; `README.md#L79-L80` says the manual path works without the model. A judge can bypass AI entirely. | Repo (future) / user |
| Substantive progress during the hackathon | **Partial / cannot be confirmed from public repo yet** | Git history: `3aad466`, `a4e3784`, `346a317` (2026-10-31); sandbox snapshot created 2026-10-30; eval report `evals/reports/20261030T151055Z-facts-v7-inline-both.md`; current worktree has uncommitted changes and new files dated 2026-11-02 | The 2026-11-02 work is **uncommitted**. A public judge sees only pushed history. Commit/push before submission; do not claim the whole project was built today. | **User** |
| Text description (features and functionality) | **Partial** | `docs/SUBMISSION_DRAFT.md` has a evidence-linked Chinese/English feature table | The Devpost text must be edited/submitted by the user; draft is not the form | **User** |
| Functional demo: repo setup/run or hosted URL | **Partial** | README “Run it locally” and “Running without credentials”; `scripts/verify.ps1` / `.sh`; no hosted URL | A is chosen; B is not deployed. Without credentials the payment and model steps stop with explicit 503; with sandbox creds the full path runs. Judges must follow setup. | Repo / **user** |
| Tools (models/AI services + how used) | **Satisfied in repo** | `backend/app/core/config.py#L36-L48` (`MODEL_PROVIDER=openai-compatible`, `MODEL_BASE_URL`, `MODEL_NAME`, sandbox PayPal); `backend/app/ai/client.py#L29-L60`; `backend/app/ai/prompts.py#L22-L43`; `backend/app/paypal/client.py#L85-L208`; report model `deepseek-v4.1-flash` | The live model name is supplied by `.env` `MODEL_NAME`; value not in repo. Devpost Tools text must be pasted by user. | Repo / **user** |
| Public code repository | **Not locally verifiable** | Remote `git@github.com:1634594707/ScopeBridge.git`; MIT `LICENSE` tracked; 24 screenshots tracked; new scripts/docs are currently untracked | Public visibility and About license are GitHub settings; current new files must be committed/pushed | **User** |
| License file visible at top/About | **Partial** | `LICENSE` is MIT at repo root | GitHub About visibility cannot be verified locally | **User** |
| Demo video <3 minutes, real device, YouTube public, no unauthorized marks/music | **Not satisfied** | `docs/DEMO_SCRIPT.md` has a 2:25 single cut; no video file is submitted; `recordings/` is git-ignored | Video must be recorded, uploaded to YouTube, link pasted; avoid third-party music/stock; see `docs/DEMO_SCRIPT.md` | **User** |
| All source/assets/instructions in repo | **Partial** | `git ls-files docs/screenshots` = 24; all 24 referenced `docs/screenshots/*.png` exist (`missing=0`); `frontend/public/{favicon,logo-mark}.svg` tracked; scripts/docs new files are untracked; `recordings/` ignored | Commit new files; do not rely on ignored recordings | **User** |
| Cross-platform reproduction | **Partial** | `scripts/verify.ps1` ran: latest 30.4s (including `uv sync`/`pnpm install`), 109 passed; `scripts/verify.sh` syntax checked with `bash:5 bash -n`; `.github/workflows/verify.yml` added | Bash script was not executed end-to-end on this Windows machine (WSL has no `/bin/bash`); GitHub Actions has not run yet | Repo / **user/CI** |
| Third-party assets / marks / music | **Partial** | App uses system fonts (`frontend/tailwind.config.js#L33-L44`); no external font/image URL in `frontend/src`; icons are `lucide-react` ISC; React/React Query MIT; diagrams embed JetBrains Mono WOFF2 with the SIL OFL text at `docs/architecture.html#L36-L129`; no audio/stock media tracked | `docs/thumbnail.png` provenance is not documented; PayPal marks appear as functional integration; the video must avoid unauthorized music/marks | **User** / repo |
| Official Rules / eligibility / third-party content | **Not locally verifiable** | The repository contains the product and license, not the Official Rules or eligibility evidence | The user must check eligibility, public repo/About, YouTube public video, and music/mark rights against the current Official Rules; do not infer approval from this audit | **User** |

## Tools paragraph (copy-ready, under 150 words)

Chinese:

> AI 使用 OpenAI-compatible 聊天补全接口（`POST {MODEL_BASE_URL}/chat/completions`，temperature 0，`response_format=json_object`，prompt `facts-v7`）。它只把客户 brief 读成五个事实：`pages`、`budget_usd`、`deadline_days`、`assets_ready`、`features`；任何金额都不进入报价。当前运行的供应商与模型名由 `.env` 的 `MODEL_NAME` 提供，仓库不硬编码；2026-10-30 的评测报告记录了一次 `deepseek-v4.1-flash` 运行。PayPal 侧使用 Orders v2 沙箱：OAuth2 token、create order（intent CAPTURE）、capture、get order；金额从服务端已确认报价读取。

English:

> AI: an OpenAI-compatible chat-completions endpoint (`POST {MODEL_BASE_URL}/chat/completions`, temperature 0, `response_format=json_object`, prompt `facts-v7`). It only extracts five facts from the brief — `pages`, `budget_usd`, `deadline_days`, `assets_ready`, `features` — and never supplies a quote amount. The running provider/model name is supplied by `MODEL_NAME` in `.env` and is not hard-coded; a recorded 2026-10-30 evaluation used `deepseek-v4.1-flash`. PayPal: Orders v2 sandbox via OAuth2 token, create order (intent CAPTURE), capture, and get order; the amount is read from the server-side confirmed quote.

Exact keys/constants used for this paragraph:

- `backend/app/core/config.py#L36-L48`: `model_provider = "openai-compatible"`, `model_base_url`, `model_api_key`, `model_name`, `paypal_env = "sandbox"`, `paypal_base_url`, `paypal_client_id`, `paypal_client_secret`.
- `backend/app/ai/prompts.py#L22-L27`: `PROMPT_VERSION = "facts-v7"`; contract keys are the five listed.
- `backend/app/ai/client.py#L39-L52`: `temperature=0`, `max_tokens=1200`, `response_format={"type":"json_object"}`, messages, `POST {base_url}/chat/completions`.
- `backend/app/paypal/client.py#L85-L208`: `/v1/oauth2/token`, `POST /v2/checkout/orders` with `intent: CAPTURE`, `POST /v2/checkout/orders/{id}/capture`, `GET /v2/checkout/orders/{id}`.
- `.env.example` leaves `MODEL_NAME` and `MODEL_BASE_URL` empty; the live values are supplied by `.env` and are not in the repository.
- `evals/reports/20261030T151055Z-facts-v7-inline-both.md#L3-L4`: recorded model `deepseek-v4.1-flash`, prompt `facts-v7`, 19 cases, one run.

## Running without credentials

See the independent “Running without credentials” section in `README.md` (added 2026-11-02). Summary:

- **Works**: app/health, sign-in, CSRF, ownership, briefs, manual scope pricing, quotes, review,
  confirmation, estimator, closed/paid read-only.
- **Stops explicitly**: model draft → `503 model_not_configured`; payment → `503
  paypal_not_configured` before the quote locks. The quote remains `CONFIRMED`; no attempt is created.
- **Cannot**: reach the PayPal approval page or complete a sandbox payment without
  `PAYPAL_CLIENT_ID/SECRET`; get model facts without `MODEL_API_KEY/MODEL_NAME`.
- The full path can be completed only with sandbox credentials; this is stated, not hidden.

## Functional demo: A vs B

**Chosen: A (judges run from the repo).** B is not deployed.

Why A is acceptable:

- The repo has setup/run instructions and an isolated one-command verification script.
- A judge with no PayPal/model credentials can still reach and interact with the main UI and the
  rule/quote/confirm flow; the two unavailable steps fail with explicit 503 messages, not crashes.
- The full payment demonstration requires sandbox credentials; the README says exactly that.

B minimum deployment (if the user later decides to host it):

1. A public host with Docker Compose and a public HTTPS URL (Render, Fly.io, a VPS, or similar).
2. PostgreSQL reachable from the backend; set `DATABASE_URL`, `SESSION_SECRET`, `APP_BASE_URL`,
   seller/client demo passwords, PayPal sandbox keys, model base/key/name.
3. Run `alembic upgrade head` and `python -m app.seed`; run uvicorn and serve the built frontend on
   the same origin with `/api` proxied to the backend.
4. Set `APP_BASE_URL` to the public URL so PayPal returns to the hosted payment page.
5. Treat registration as public: add rate limits or a demo allowlist; sandbox only; budget model
   calls and PayPal calls. Cost/risk: model tokens, sandbox credentials, abuse of public
   registration, and a public payment surface. That is why B is not the default.

## AI load-bearing: risk and smallest fix

Current evidence that AI is optional:

- `README.md#L79-L80`: “the manual path works without the model”.
- `backend/app/quotes/service.py#L26-L60`: `create_quote` checks proposal feasibility and revision,
  not the presence of an `ai_extractions` row.
- `frontend/src/pages/RequirementPage.tsx` shows the model card and the manual `ScopeEditor` as
  separate paths.
- `backend/tests/test_ai_extraction.py` proves the model path; the manual path is covered by
  `test_api_quote_flow.py` without any extraction.

Minimal options that keep pricing in `app/rules/`:

1. **Clarification gate (recommended).** Require a current-revision extraction before the seller can
   issue a quote; surface the model's `questions` and `unsupported_requests` to the client, and
   require answers/acknowledgement. If the model is unavailable, record an explicit manual
   clarification instead of silently bypassing. Impact: `quotes/service.create_quote` gains a check;
   `ai/service` exposes questions (already present); `PortalPage`/`RequirementPage` add a
   clarification step; tests. This is the smallest change that puts AI on the critical path.
2. **AI change summary.** On each new revision, use the model facts to produce a “what changed”
   summary shown next to `QuoteDiff`; require the client to acknowledge it before confirm. Impact:
   `ai/service`, `PortalPage`, `QuoteDiff`; no pricing changes.

Do not make the model price or approve; do not remove the explicit manual fallback without
credentials. Both options are proposals only; no code was changed for them.

## Video cut

`docs/DEMO_SCRIPT.md` now has a **2:25 single cut**:

- keep the happy path: brief → facts/options → quote → review → client confirm → PayPal capture →
  snapshot/closed;
- keep a 35-second recovery segment: `RECONCILING` → `Retry create` → order id → `COMPLETED`;
- cut landing motion/hover, full sign-in transitions, model latency, long quote scrolling and the
  Path C close take; explain them with subtitles;
- do not use a design mockup, unlicensed music or unlicensed third-party marks in the video.

No video has been recorded; the user must record/upload it.

## Required user-owned items

- Commit and push the current worktree; make the repository public; confirm the MIT license is
  visible in GitHub About.
- Record and upload a public YouTube video under 3:00, then paste the URL into Devpost.
- Edit and submit the Devpost text, Tools paragraph, project description and team information.
- Supply real user trial/interview feedback if claiming any; otherwise say it was not run.
- Confirm rights/provenance of `docs/thumbnail.png` and any screenshot/third-party mark used in the
  video; ensure no unlicensed music/stock footage.
- Supply PayPal sandbox credentials and model key at runtime; do not commit them.

## Not locally verified

- Public GitHub visibility and About license: cannot be checked from this machine.
- Demo video existence/URL: no video is recorded; `recordings/` is local and ignored.
- GitHub Actions workflow run: the file is added but has not executed.
- Full bash verification run: only `bash -n` in a Linux container; the PowerShell script is the one
  actually run end-to-end.
- Hosted demo: not deployed.
- Real user trial: not run.
- The live `MODEL_NAME` value in `.env`: not in the repository; only the recorded evaluation report
  names `deepseek-v4.1-flash`.
- `docs/thumbnail.png` provenance: no source/license note found.
