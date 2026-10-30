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

## What is implemented (M0–M3)

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
- **Local-first operation** — PostgreSQL in Docker, single operator account; the model is the only
  external service, and the manual path works without it.

Not implemented yet (planned, see `docs/FORMAL_PROPOSAL.md`): PayPal sandbox create/capture/reconcile
(M4), evaluation suite at 20 cases (M5), demo video and submission material (M6).

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
    R --> SR
    AI --> RULES
    PROP --> RULES
    QUOTE --> RULES
    AUTH --> DB
    AI --> DB
    REQ --> DB
    PROP --> DB
    QUOTE --> DB
    SR --> DB
    AI -.-> LLM
    QUOTE -.-> PG
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
   The quote turns read-only.

Try an infeasible scope too: three pages against a $500 budget returns
`Scope totals $700.00 against a budget of $500.00; short by $200.00.`

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
| `GET` | `/api/health` | public |

Errors are always `{"code", "message", "details?"}` — no stack traces, SQL or tokens.

---

## Tests

```bash
cd backend
uv run pytest -q            # 40 tests
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

Fixture cases live in `evals/` with their expected verdicts; changing a rule means updating the case
first, not loosening the assertion.

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
- **Secrets** stay in `.env` (git-ignored). The PayPal sandbox credentials used during development are
  not part of the repository; only `.env.example` is tracked.

### Known limitations

- `POST /api/requirements` has no rate limit; add one before exposing the app publicly.
- Quote immutability is enforced in the application layer, not by database triggers.
- No audit log beyond message authorship, revisions, quote timestamps and model calls.
- Model calls are single-attempt: an invalid answer costs one click and returns `422`; the studio
  prices by hand. No automatic repair prompt or retry, so failures stay visible in the evidence table.
- `features` come back as free strings; codes that are not capabilities appear under
  "asked for but not offered" instead of being mapped silently.
- The demo price list is fictional; it is a product fixture, not a market rate.

## License

MIT — see [LICENSE](LICENSE).
