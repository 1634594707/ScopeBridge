# Agent Note: The backend is a modular monolith with domain packages, and pricing plus feasibility collapse into a zero-IO pure-function layer

Status: implemented

## Problem

The project had two weeks to deliver a closing main line a judge can actually operate, while being
able to explain the boundary of "the AI proposes, the program judges, the human confirms". If price
computation were scattered across routers, models and future model calls, nobody could prove the
amount was not rewritten by the model or the front end; and a microservice split would eat the
implementation time of a single developer.

## Decision

The backend is a modular monolith in one process, split by domain: `accounts`, `service_rules`,
`requirements`, `proposals`, `quotes` — each package with its own models / schemas / service /
router. Cross-package calls go through the other package's service only; tables are never read
across packages. `app/rules/` is a standalone zero-IO pure-function layer (`price_scope` /
`evaluate`): input is a rule projection plus a scope input, output is a `ValidationResult`; it knows
nothing of the database, network or clock (`today` is passed in by the caller). State transitions
collapse the same way into the pure function `quotes/states.transition`; illegal transitions raise
409 directly. Data access uses SQLAlchemy 2 synchronous sessions + psycopg3, migrations use Alembic;
amounts are always integer cents.

## Alternatives considered

- **Microservice split (requirements / proposals / quotes / payments deployed separately)**: the
  strongest case is physical module isolation, so a payment-chain failure cannot take quoting down.
  Rejected: this project has one developer and one demo main line; cross-service auth, transactions
  and local orchestration would directly crowd out feature time. A modular monolith also preserves
  the boundary at this stage via "no cross-package table reads"; splitting can wait until there is a
  real independent-scaling need.
- **Repository pattern (Repository + Unit of Work)**: the strongest case is decoupling domain logic
  from persistence, with in-memory repositories for fast unit tests. Rejected: the domain logic here
  is already extracted into pure functions, so real test value concentrates in the rules and state
  machine — neither needs a database stand-in; another repository layer would only add mapping
  boilerplate between records and domain objects.
- **Async SQLAlchemy / asyncpg**: the strongest case is better concurrent throughput under FastAPI,
  suited to I/O-bound work. Rejected: after M4 introduces payments, the critical invariant is
  "commit the local record first, then issue the external request", and synchronous sessions make
  that ordering obvious in the code structure; demo-scale concurrency is not a bottleneck.
- **Adopt a state-machine library**: the strongest case is declarative, visualisable states and
  transitions. Rejected: there are only 4 states and 4 legal transitions; hand-written guards +
  unit tests are more controllable and avoid the library's implicit fault tolerance.

## Consequences

- Benefit: amounts and feasibility have exactly one computational entry point; when M3 attached the
  model, its output had to pass through the same validator; the pure-function layer runs the full
  case set without a database, tests finish within 3 seconds.
- Benefit: module boundaries are maintained by directory layout and import direction; the new
  `payments` package had an obvious home.
- Cost: synchronous sessions limit throughput under high concurrency — a known trade-off; module
  boundaries currently rely on convention and code review, with no automated dependency check.
- Cost: quote-version immutability is enforced only in the application layer; no database trigger
  blocks updates. Accepted for the demo; if there is no slack before M4 it stays as-is and is noted
  in the docs.

## Testing

`backend/tests/test_pricing.py`, `test_feasibility.py`, `test_state_machine.py` cover the
pure-function layer; `test_api_quote_flow.py` covers database-backed flows and state transitions;
`evals/cases/*.json` is the fixed case set, replayed case by case by `test_eval_cases.py`.
