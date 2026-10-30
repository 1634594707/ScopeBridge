# ScopeBridge

**An agreement desk for studio work.** ScopeBridge turns an ambiguous client request into a priced,
rule-checked scope, then carries the exact same version through studio review, client confirmation
and (from M4) a PayPal sandbox payment.

The product is built around one idea: **the model may propose, but only a program prices, only a
human reviews, and only the client confirms.** Every line on a quote points back to the rule that
priced it and the client message that justified it.

> 中文设计文档：`docs/FORMAL_PROPOSAL.md`（正式方案）、`docs/DEVELOPMENT.md`（接口与里程碑）、
> `docs/architecture.html` / `docs/workflow.html`（架构图与流程图）。界面文案为英文。

![Landing page](docs/screenshots/01-landing.png)

---

## The demo in one paragraph

Maya asks for a three-page site with on-site ordering, a $500 budget, live in two weeks, no assets
ready. The studio prices two scopes: a one-page launch that includes an external ordering link
(within budget) and a two-page option with copywriting ($250 over). The over-budget scope stays on
screen with its exact violation instead of being hidden. Maya picks the feasible scope, the studio
reviews the quote, Maya confirms that version, and the quote becomes read-only. Any new client
message after that creates a new revision and supersedes open drafts — never edits history.

| Seller console | Requirement workspace |
| --- | --- |
| ![Console](docs/screenshots/02-seller-console.png) | ![Workspace](docs/screenshots/03-requirement-workspace.png) |

| Quote (confirmed) | Client portal |
| --- | --- |
| ![Quote](docs/screenshots/04-quote-confirmed.png) | ![Portal](docs/screenshots/05-client-portal.png) |

---

## What is implemented (M0–M4)

- **Versioned service rules** — base page, extra pages, add-ons, capability list, exclusions and
  lead time are stored as an immutable rule version; historical quotes keep their original numbers.
- **Public client intake** — a brief becomes a requirement with a private, single-requirement link.
- **Revisioned messages** — every append carries `expected_revision`; stale writes return `409`.
- **Rule-checked scopes** — the studio enters a scope (pages, add-ons, requested features, assets),
  and the server prices and judges it. Up to two candidate scopes per revision.
- **Client comparison** — feasible and infeasible scopes side by side, with budget delta, exclusions
  and explicit unsatisfied conditions.
- **Quote versions** — generated from a feasible scope with line items, rule references and source
  message references; `DRAFT → REVIEWED → CONFIRMED`, with `SUPERSEDED` on change.
- **Two identity paths** — seller session cookie + CSRF for writes; customer bearer token scoped to
  one requirement.
- **Model draft (facts only)** — one click sends the brief to an OpenAI-compatible model, which
  returns five facts (`pages`, `budget_usd`, `deadline_days`, `assets_ready`, `features`). The studio
  turns those facts into at most two options and prices them; the model never supplies an amount.
  Every call is stored in `ai_extractions` with model, prompt version, raw output, latency and error.
- **PayPal sandbox payment** — the client confirms a quote, then pays through PayPal Orders v2
  (`create → approve → capture`). The quote is locked before the first external call; the amount is
  read from the confirmed quote on the server; a lost capture response parks the attempt in
  `RECONCILING` until the original order is queried. A successful capture writes an immutable order
  snapshot in the same transaction as the `PAID` transition.
- **Version diff** — when a quote is reissued, the new version shows what changed against the
  previous one, line by line, with the total delta.
- **Structured change requests** — the client can change the brief *and* the budget, deadline or
  material state from the portal; the next quote prices the new record, and a stale revision returns
  `409` without losing what was typed.
- **Recovery when PayPal never answers** — an attempt with no order id can be retried with the same
  `PayPal-Request-Id` (bounded), or closed by the studio after a written check, which unlocks the
  quote and records who closed it and why.
- **Comparative evaluation** — 19 fixed cases run through both a one-shot "model quotes it" arm and
  the facts-and-rules pipeline, with unparseable answers counted as failures.
- **Local-first operation** — PostgreSQL in Docker, single operator account; the model and PayPal are
  the only external services, and the manual path works without the model.

Not implemented yet (planned, see `docs/FORMAL_PROPOSAL.md`): evaluation suite at 20 cases (M5),
demo video and submission material (M6); refunds, partial captures and unattended reconciliation are
out of scope for the hackathon build.

| Payment on the client portal | Payment history in the console |
| --- | --- |
| ![Payment panel](docs/screenshots/09-payment-panel.png) | ![Payment history](docs/screenshots/10-payment-history.png) |

| Version diff |
| --- |
| ![Quote diff](docs/screenshots/11-quote-diff.png) |

| Model draft | Options it produced |
| --- | --- |
| ![Model draft](docs/screenshots/07-model-draft.png) | ![Model options](docs/screenshots/08-model-options.png) |

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser["Browser (English UI)"]
        A["Client intake and portal"]
        B["Seller console"]
        C["Quote document"]
    end
    subgraph API["FastAPI modular monolith"]
        R["api router"]
        AUTH["accounts: session + portal token"]
        REQ["requirements"]
        AI["ai: fact extraction"]
        PROP["proposals"]
        QUOTE["quotes: state machine"]
        PAY["payments: lock, capture, reconcile"]
        RULES["rules: pure functions"]
        SR["service_rules"]
    end
    DB[("PostgreSQL 18")]
    LLM["OpenAI-compatible model (M3)"]
    PG["PayPal sandbox (M4)"]

    A --> R
    B --> R
    C --> R
    R --> AUTH
    R --> REQ
    R --> AI
    R --> PROP
    R --> QUOTE
    R --> PAY
    R --> SR
    AI --> RULES
    PROP --> RULES
    QUOTE --> RULES
    PAY --> QUOTE
    AUTH --> DB
    AI --> DB
    REQ --> DB
    PROP --> DB
    QUOTE --> DB
    PAY --> DB
    SR --> DB
    AI -.-> LLM
    PAY -.-> PG
```

Dependency direction is one-way: `router → service → rules/models`. `app/rules/` has no database,
network or clock access — `today` is passed in — so model output passes through the same functions as
a hand-typed scope.

Money is always integer minor units (cents) in USD. The client never sends an amount.

### Model boundary: facts, not proposals

The model returns a five-key fact sheet and nothing else. Anything out of shape is rejected whole and
recorded, never coerced:

```
{"pages": 3, "budget_usd": 500, "deadline_days": 14,
 "assets_ready": false, "features": ["landing_pages", "online_ordering"]}
```

`app/ai/candidates.py` then builds at most two options — "As briefed" and, when that fails, a
one-page scope that keeps only capabilities the studio actually offers — and `app/rules` prices both.
`budget_usd` from the model is displayed as "what the model read"; the authoritative budget comes from
the stored client message.

Measured against this gateway (2026-10-30, `deepseek-v4.1-flash`): asking for a nested object with
candidate scopes matched the schema 0/5 times, `response_format: json_schema` was accepted but not
enforced, and a persona-style prompt produced prose every time. The five-key sheet with a plain-text
brief succeeded 5/5 at 2.1–3.2 s. Reasoning and rejected options:
`.agents/notes/implemented/architecture/2026-10-30-model-boundary-facts-not-scopes.md`.

---

## Run it locally

**Prerequisites:** Docker Desktop, [uv](https://docs.astral.sh/uv/), Node 20+ with pnpm.

```bash
git clone git@github.com:1634594707/ScopeBridge.git
cd ScopeBridge

# 1) environment
cp .env.example .env          # then set DATABASE_URL, SESSION_SECRET, SELLER_PASSWORD
                              # optional: MODEL_BASE_URL / MODEL_API_KEY / MODEL_NAME
                              # APP_BASE_URL must match the origin you open in the
                              # browser (4173 for preview, 5173 for dev): PayPal
                              # sends the buyer back to that exact address.

# 2) database (PostgreSQL 18 on port 55433, isolated from any local instance)
docker compose up -d

# 3) backend
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.seed     # seller account, rule v1, one demo brief
uv run uvicorn app.main:app --port 8000

# 4) frontend (new terminal)
cd frontend
pnpm install
pnpm dev                      # http://127.0.0.1:5173
```

If `pnpm dev` fails on your machine with esbuild "Access is denied" errors, run the production bundle
instead — it is the same application, served by Vite's preview server:

```bash
cd frontend
pnpm build
pnpm exec vite preview        # http://127.0.0.1:4173
```

### Demo walkthrough

1. **Client** — open `/start`, submit a brief. You land on a private portal `/r/<token>`.
2. **Studio** — open `/signin`, use the seller credentials from `.env`
   (seed value in this repo's local `.env` is `seller@scopebridge.local` / `ScopeBridge-2026-demo`).
3. Open the brief in `/console`. Optionally press **Draft with the model** to see the extracted facts
   and two priced options; **Use this scope** copies one into the editor. Then **Price this scope**
   and **Draft quote**.
4. On the quote page press **Review and issue**.
5. **Back as the client** — open the private link, choose the scope, press **Confirm this version**.
   The quote turns read-only and the payment card appears.
6. Press **Continue to PayPal**, sign in with a **Sandbox Personal** account from
   <https://developer.paypal.com/dashboard/accounts>, and approve. PayPal returns you to
   `/pay/<payment-id>`, which confirms the payment automatically; the server verifies amount and
   currency, marks the quote `PAID` and writes the order snapshot.

A two-path shooting script (happy path and the "no order id" recovery) is in
[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

Try an infeasible scope too: three pages against a $500 budget returns
`Scope totals $700.00 against a budget of $500.00; short by $200.00.`

To demonstrate recovery without a stalled network, stop the API between approval and capture, press
**I approved — capture now** (the request fails), start the API again, then press
**Verify with PayPal** in the seller console: the attempt moves from `VERIFYING` to `COMPLETED`.

---

## API surface

| Method | Path | Who |
| --- | --- | --- |
| `POST` | `/api/session` · `DELETE /api/session` · `GET /api/session` | seller |
| `GET` | `/api/service-rules` | public |
| `POST` | `/api/requirements` | public intake (creates the portal token once) |
| `GET` | `/api/requirements` · `/api/requirements/{id}` | seller |
| `POST` | `/api/requirements/{id}/messages` | seller (CSRF) |
| `POST` | `/api/requirements/{id}/extractions` · `GET .../extractions/latest` | seller (CSRF) |
| `POST` | `/api/requirements/{id}/proposals` | seller (CSRF) |
| `POST` | `/api/requirements/{id}/quotes` | seller (CSRF) |
| `POST` | `/api/quotes/{id}/review` | seller (CSRF) |
| `GET` | `/api/portal` · `POST /api/portal/messages` | client token |
| `POST` | `/api/portal/proposals/{id}/select` | client token |
| `POST` | `/api/portal/quotes/{id}/confirm` | client token |
| `POST` | `/api/portal/quotes/{id}/payment-attempts` | client token + `Idempotency-Key` |
| `GET` | `/api/portal/payments/{id}` · `POST .../capture` | client token |
| `POST` | `/api/payments/{id}/reconcile` · `/retry-create` · `/close` | seller (CSRF) |
| `GET` | `/api/requirements/{id}/payments` · `/order` | seller |
| `GET` | `/api/orders/{id}` | seller |
| `GET` | `/api/health` | public |

Errors are always `{"code", "message", "details?"}` — no stack traces, SQL or tokens.

---

## Tests

```bash
cd backend
uv run pytest -q            # 78 tests
uv run ruff check .
```

- `test_pricing.py` / `test_feasibility.py` — pure rule layer (three pages = 70000 cents, budget gap,
  unsupported capability, lead time, missing information).
- `test_state_machine.py` — every illegal quote transition returns `409`.
- `test_api_auth.py` — bad password, throttling, CSRF, unknown portal token, cross-seller access.
- `test_api_quote_flow.py` — intake → scope → select → quote → review → confirm, plus revision
  supersession.
- `test_eval_cases.py` — replays the five fixed cases in `evals/cases/`.
- `test_ai_extraction.py` — server-built options, model money ignored, prose/extra keys/out-of-range
  pages rejected, evidence row written, empty latest draft returns `null`.
- `test_api_payment.py` — quote lock on attempt, idempotency replay and conflict, capture writes one
  snapshot, amount mismatch stays in `RECONCILING`, lost response recovered by reconcile, declined
  capture unlocks the quote, cross-tenant access returns 404.

Fixture cases live in `evals/cases.json` (20 cases, 19 of them rule-level) with their expected
verdicts; changing a rule means updating the case first, not loosening the assertion.

### Comparative evaluation

```bash
cd backend
uv run python ../evals/run_eval.py --runs 3 --workers 1 --timeout 120 --pause 2
```

Two arms, same briefs, same published terms, same model:

- **baseline** — one prompt asks the model for pages, add-ons, a total and a feasibility claim. The
  claimed total is compared with what the rules would charge for the scope it named.
- **pipeline** — the model returns the five facts, the server builds at most two options and prices
  them.

Reports land in `evals/reports/<timestamp>.{json,md}` with per-case verdicts, average and p95 latency,
and token counts. Nothing in the report is estimated: failed calls are counted as failures.

Every rate names its denominator. `all attempts` includes unparseable and failed calls; `parsed`
is used only where the label says so. Pipeline "unsafe releases" is not assumed to be zero: each
option's displayed price and verdict are re-computed from the rules and mismatches are counted.

Latest recorded run (`evals/reports/20261030T151055Z-facts-v7-inline-both.md`, 19 cases, one run
each, sequential):

| metric | baseline | pipeline |
| --- | --- | --- |
| parse rate | 18 / 19 | 19 / 19 |
| transport failures | 1 | 0 |
| claims the rules reject | 2 | n/a |
| wrong or missing price | 0 of the parsed | n/a (server prices) |
| unsafe releases (measured) | 2 | 0 |
| original request satisfied | n/a | 6 |
| narrowed option available | n/a | 6 |
| honest "no solution" | n/a | 7 |
| average latency | 4.3 s | 4.3 s |

An earlier run of the same harness (`20261030T132147Z.md`) had only 7/19 pipeline answers parse.
The cause was not the wording but the channel: this gateway did not deliver the system message, so
the contract never reached the model. The contract is now sent with the payload as well; parse rate
went from 47% to 100% on the same cases, and the change is recorded in
`.agents/notes/implemented/architecture/2026-10-30-contract-must-travel-with-payload.md`.

---

## Engineering notes

- **Modular monolith** with domain packages (`accounts`, `service_rules`, `requirements`,
  `proposals`, `quotes`); cross-package calls go through services, never through another package's
  tables.
- **Pure decision layer** (`app/rules/`): pricing and feasibility are functions of `(RuleSet,
  ScopeInput)`, with `today` injected, so verdicts are reproducible and unit-testable without a
  database.
- **Revision CAS instead of locks**: `expected_revision` guards appends; quotes are immutable once
  created, and a new revision supersedes open drafts.
- **Decision notes** live in `.agents/notes/` (`implemented/architecture/`), including a STRIDE pass
  over sessions, portal tokens and CSRF. Workflow rules for this repo are in `AGENTS.md`.
- **Model boundary**: `app/ai/client.py` is the only place that speaks HTTP to a model; failures are
  surfaced as `502`, invalid shapes as `422`, and every attempt (including failures) is stored in
  `ai_extractions` with its prompt version.
- **Payments lock before they call out**: `app/payments/service.py` commits the attempt and the
  `PAYMENT_LOCKED` state before touching PayPal, then only a verified `COMPLETED` capture can write the
  snapshot and move the quote to `PAID`. See
  `.agents/notes/implemented/architecture/2026-10-30-payment-lock-and-verify.md`.
- **Secrets** stay in `.env` (git-ignored). The PayPal sandbox credentials used during development are
  not part of the repository; only `.env.example` is tracked.

### Known limitations

- `POST /api/requirements` has no rate limit; add one before exposing the app publicly.
- Quote immutability is enforced in the application layer, not by database triggers.
- No audit log beyond message authorship, revisions, quote timestamps, model calls and payment
  attempts.
- Model calls are single-attempt: an invalid answer costs one click and returns `422`; the studio
  prices by hand. No automatic repair prompt or retry, so failures stay visible in the evidence table.
- `features` come back as free strings; codes that are not capabilities appear under
  "asked for but not offered" instead of being mapped silently.
- Payments are sandbox-only. There are no webhooks: an unclear capture is resolved by the seller
  pressing **Verify with PayPal**, retrying the create call, or closing the attempt with a written
  note. Closing a quote unlocks it only after that human check, so a quote can stay
  `PAYMENT_LOCKED` until someone acts.
- Closing an attempt is a human judgement; the server cannot prove that PayPal has no order. The
  note and the resolving seller are stored on the attempt for review.
- No refunds, partial captures or unattended reconciliation job. `PAYPAL_MERCHANT_ID` is optional; when
  unset only amount and currency are verified, not the payee.
- The demo price list is fictional; it is a product fixture, not a market rate.

## License

MIT — see [LICENSE](LICENSE).
