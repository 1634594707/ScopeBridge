# ScopeBridge development record

**This document records the current implementation and is updated with the code.** Planning and
acceptance criteria live in `FORMAL_PROPOSAL.md` (v3.0); the pre-work baseline is archived at
`archive/PROJECT_PLAN-v2.md`; the English entry point for judges is the root `README.md`.

## Milestone status

| Milestone | Contents | Status |
| --- | --- | --- |
| M0 | Scaffolding: uv + FastAPI + SQLAlchemy/Alembic, Vite/React/Tailwind, Docker PostgreSQL, health check | done |
| M1 | Pure-function pricing and feasibility validator + five fixed cases | done |
| M2 | Requirement / proposal / quote / review / confirm, permissions and version conflicts | done |
| M3 | Model integration: facts only; the server builds and prices candidate options | done |
| M4 | PayPal sandbox create, approve, capture and recovery | done (one real $500 sandbox payment) |
| M5 | Version diff, structured change requests, 19-case two-arm evaluation | code complete; real user trial not run |
| M6 | Clean-environment reproduction, demo video, submission materials | pending |

## Layout and modules

```
backend/app/
  core/           config, database session, unified error body, password hashing
  accounts/       user accounts (seller and client), shared sessions, sign-in throttling, CSRF
  service_rules/  immutable service rule versions and the public scope estimator
  requirements/   requirements and revisioned messages (expected_revision CAS)
  proposals/      candidate options (program-priced and judged, at most two per revision)
  quotes/         quote versions, line items, state machine
  payments/       payment attempts, verification, recovery, order snapshots
  paypal/         Orders v2 adapter (the only place that issues external HTTP)
  ai/             model client, prompts, fact validation, candidate construction
  rules/          pure-function pricing and feasibility, zero IO
frontend/src/     pages/, components/, lib/{api,types,format}
evals/            cases.json, run_eval.py, metrics.py, reports/
```

## Environment variables

`.env` (not tracked) contains at least: `DATABASE_URL`, `SESSION_SECRET`, `SELLER_PASSWORD`,
`CLIENT_EMAIL`, `CLIENT_PASSWORD`, `MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME`,
`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_BASE_URL`, `APP_BASE_URL`. Optional:
`PAYPAL_MERCHANT_ID`, `PAYPAL_TIMEOUT_SECONDS`, `ARGON2_MEMORY_COST`.

`APP_BASE_URL` must match the address actually opened in the browser (4173 for preview, 5173 for
dev): PayPal sends the buyer back to `{APP_BASE_URL}/pay/{attempt_id}`.

## Data model (as implemented)

| Table | Notes |
| --- | --- |
| `service_rule_versions` | Immutable rule JSON: base page price, extra page price, add-on catalogue, capability list, exclusions, lead time |
| `users` | One table for both roles (`role` = `SELLER` or `CLIENT`); the seller is the single seeded operator, clients register themselves |
| `user_sessions` | One session table for both roles: SHA-256 token hash, CSRF token, expiry (12 h) |
| `requirements` / `requirement_messages` | `seller_id` (the desk) and `client_id` (the owner); `status` moves `OPEN → CLOSED` when the order snapshot is written and `CLOSED` rejects new messages, proposals and quotes; messages carry budget, deadline, asset state, revision number, with omitted fields inherited from the newest non-null value |
| `proposals` | Options bound to a rule version, with inclusions, exclusions, validation results |
| `quote_versions` / `quote_items` | Version number, line items, `rule_ref`, source messages, review/confirmation times, state |
| `payment_attempts` | Idempotency key, PayPal order/capture id, state, `retry_count`, closing seller and rationale; a brief cannot be deleted while an attempt is non-terminal or carries a PayPal id |
| `order_snapshots` | Unique per successful payment; written in the same transaction as `PAID`, immutable afterwards |
| `ai_extractions` | Every model call: model name, prompt version, input message ids, raw output, parsed result, error code, latency |

## API (as implemented)

| Method and path | Permission |
| --- | --- |
| `POST /api/session`, `POST /api/client-session` | seller / client sign-in (shared throttling) |
| `POST /api/clients` | public — client registration, opens the first session |
| `GET /api/session` | any signed-in account (returns `{account, csrf_token}` with the role) |
| `DELETE /api/session` | any signed-in account (CSRF) |
| `GET /api/service-rules` | public |
| `POST /api/service-rules/estimate` | public; prices a hypothetical scope from `pages` + `addon_codes` only (no amount in the request) |
| `POST /api/requirements` | client (CSRF); the brief is owned by the signed-in client |
| `GET /api/requirements` | seller; each summary carries `deletable` (false once an order snapshot exists) |
| `GET /api/requirements/{id}` | seller |
| `DELETE /api/requirements/{id}` | seller (CSRF); 409 `payment_completed` once an order snapshot exists |
| `POST /api/requirements/{id}/messages` | seller (CSRF) |
| `POST /api/requirements/{id}/proposals` | seller (CSRF) |
| `POST /api/requirements/{id}/extractions`, `GET .../latest` | seller (CSRF) |
| `POST /api/requirements/{id}/quotes` | seller (CSRF) |
| `POST /api/quotes/{id}/review` | seller (CSRF) |
| `GET /api/portal/briefs` | client — the client's own briefs |
| `GET /api/portal/{requirement_id}`, `POST /api/portal/{requirement_id}/messages` | client + ownership |
| `POST /api/portal/{requirement_id}/proposals/{id}/select` | client + ownership (CSRF) |
| `POST /api/portal/{requirement_id}/quotes/{id}/confirm` | client + ownership (CSRF) |
| `POST /api/portal/requirements/{requirement_id}/quotes/{quote_id}/payment-attempts` | client + ownership (CSRF) + `Idempotency-Key` |
| `GET /api/portal/payments/{id}`, `POST .../capture` | client + ownership (capture: CSRF) |
| `POST /api/payments/{id}/reconcile` / `/retry-create` / `/close` | seller (CSRF) |
| `GET /api/payments/attention` | seller; every non-terminal attempt (`CREATING`, `AWAITING_APPROVAL`, `CAPTURING`, `RECONCILING`) plus `FAILED` attempts on unpaid quotes, with client and quote number |
| `GET /api/requirements/{id}/payments`, `/order` | seller |
| `GET /api/orders/{id}` | seller |
| `GET /api/health` | public |

Error bodies are always `{code, message, details?}`; writes carry `Idempotency-Key` and
`expected_revision`, and conflicts return `409`.

## State machines and recovery

- Requirement: `OPEN → CLOSED` in the same transaction that writes the order snapshot. `CLOSED` is
  terminal for new messages, proposals and quotes; new work needs a new brief. Closing a payment
  attempt by hand leaves the brief `OPEN` because the quote can still be paid.
- Quote: `DRAFT → REVIEWED → CONFIRMED → PAYMENT_LOCKED → PAID`; a revision change marks
  `DRAFT`, `REVIEWED` and `CONFIRMED` versions `SUPERSEDED`. Unlocking has exactly two paths: the
  server verifies a definitive "no successful capture", or the seller closes the attempt manually
  after checking PayPal.
- Payment: `CREATING → AWAITING_APPROVAL → CAPTURING → COMPLETED`; unknown outcomes enter
  `RECONCILING`; definitive failures enter `FAILED`; manual closing enters `ABANDONED`. A
  `CREATING`/`CAPTURING` attempt left by a process stop is parked in `RECONCILING` after 120
  seconds by startup/request-time recovery, not by a background job.
- Status writes are conditional updates: a late error branch never overwrites `COMPLETED`, and a
  verified capture repairs a quote that an earlier failure had unlocked to `CONFIRMED` instead of
  returning `409` after the charge.
- Create with no receipt: retry with the same `PayPal-Request-Id`, at most 2 times; still failing
  goes to manual closing (the seller confirms the PayPal check in the request and writes a rationale
  of at least 10 characters, recording who closed it and when).
- Lost capture response: query the original order; `COMPLETED` backfills the snapshot, `APPROVED`
  resumes the capture, `VOIDED`/`EXPIRED` is judged a failure. `ORDER_ALREADY_CAPTURED` is first
  queried at PayPal; it never marks an attempt `RECONCILING` blind.

## Model contract

- Prompt version: `facts-v7`. The model returns exactly five keys: `pages`, `budget_usd`,
  `deadline_days`, `assets_ready`, `features`; `extra="forbid"` — prose, code fences and extra keys
  are all `422`.
- **The contract must travel with the user message**: measured on this gateway, system messages are
  not delivered, so given only the brief the model invents its own schema. Re-wording the prompt did
  nothing; changing the channel did (parse rate 47% → 100%).
- Candidate options are built by `app/ai/candidates.py` and priced by `app/rules`; any amount from
  the model is discarded.

## Evaluation

19 rule-level cases (`evals/cases.json`) + 1 flow-level case (covered by the API tests).
`evals/metrics.py` defines the measurement basis: every rate uses **call count** as its denominator,
and the pipeline's unsafe releases are recomputed at runtime by calling `evaluate` again — never
hardcoded.

```bash
cd backend
uv run python ../evals/run_eval.py --runs 1 --workers 1 --timeout 90 --pause 1 --tag <label>
```

Reports land in `evals/reports/<timestamp>[-<tag>].{json,md}`.

## Deviations from the original plan

| Planned | Actual | Reason |
| --- | --- | --- |
| Model outputs candidate options + evidence | Model outputs facts only; the server builds candidates | Nested output is unstable on this gateway; the combinatorial judgement is inherently a rules problem |
| Payment endpoint at `/api/quotes/{id}/payment-attempts` | Moved to `/api/portal/requirements/{requirement_id}/quotes/{quote_id}/payment-attempts` | The initiator is the client, so the permission path must match the client identity |
| Client submits the amount | The request body carries a budget and deadline, never a quote or payment amount | The rules layer is the single source of prices; the budget is a client constraint, not a charge |
| Evaluation runs each case 3 times | Recorded as 1 full run | Gateway timeouts broke multi-run attempts; the report says so, and single-run numbers were not padded |
| Playwright verifies the main browser flow (proposal §13) | API tests and the manual demo script are the browser evidence; no Playwright/E2E suite is in this build | Browser automation was not added; the limitation is stated in README and the proposal was corrected |
| No registration; clients hold a private link per requirement (proposal v3.0 §6/§7) | Client accounts: both sides sign in, briefs are owned by the client account, portal-token auth removed | Product decision on 2026-10-31: attribution to a signed-in identity is what makes the record auditable ("对账"); ownership checks replace the unguessable-link mechanism |

## Verification commands before submitting

```bash
cd backend && uv run pytest -q && uv run ruff check .
cd frontend && pnpm exec tsc -b && pnpm exec vite build
scripts/verify.ps1                 # or: bash scripts/verify.sh
scripts/prepare-demo-pathb.ps1     # Path B isolated data
npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
```

Playwright/E2E is not implemented in this build; the browser flow is the manual script in
`DEMO_SCRIPT.md`. M6 video and real user trial remain pending.
