# Archived: ScopeBridge project plan and technical design v2.0

> **This document was superseded by ../FORMAL_PROPOSAL.md (v3.0) and is kept only as a historical
> baseline; it is no longer updated.**
> It describes the goals set before implementation began and does not reflect the current build;
> for the current state see ../DEVELOPMENT.md and the root README.md.

---

# ScopeBridge project plan and technical design

30 October 2026 · v2.0 · pre-work baseline · independent entry

## Confirmed direction

ScopeBridge is a constrained service-closing assistant that helps freelance web designers turn
conflicting requests into executable, confirmable, payable service agreements. Core capabilities are
option generation under constraints, linking requirements to pricing grounds, and a recoverable
payment flow. This document described pre-development goals; it does not claim features were
implemented and promises no award.

The stack is fixed: React + TypeScript + Vite front end, Python + FastAPI back end, Pydantic
validation, SQLAlchemy + Alembic for data access and migrations, PostgreSQL storage. The back end is
one process with business modules and an explicit state machine. The model uses one provider with
structured output; the exact model is pinned with small samples, and model and prompt versions are
frozen before evaluation. No Go, no multi-agent frameworks, no vector databases, no message queues,
no extra microservices.

## Product and core demo

A client asks for "a $500 three-page site with online ordering, live next week". The system extracts
budget, page count, features, deadline and asset conditions, and links the original message; at most
three key clarification questions per round. The program identifies constraint conflicts from the
service rules, the AI proposes at most two alternatives, the program verifies them and presents the
trade-offs. When no feasible solution exists, the unmet conditions are returned explicitly — no
invented discounts or delivery dates.

Demo price list: base single page 500 USD, each extra page 100 USD, includes mobile adaptation and
two revision rounds. An external ordering link can be included in the single page, but the absence
of on-site ordering or payment systems must be stated. Standard lead time is five business days
after assets are complete, excluding domain and hosting; the final delivery date is confirmed by the
provider. The three-page scope is 700 USD; 500 USD admits only a narrowed, feasible option. All
amounts and conditions are demo configuration, not market rates.

Every quote shows its source messages, matching service rules, inclusions and exclusions. The client
picks an option, the provider reviews, the client confirms the final version, then the PayPal
sandbox payment runs. An add-on request produces a diff and a fresh confirmation; a timed-out
payment response is demonstrated by querying the original transaction to recover state. Only the
current, explicit stage is payable; no automatic subsequent charges.

## Pages and scope

The first version contains four page groups: service configuration, client requirement with option
comparison, provider review, and order detail. Core pages foreground unconfirmed conditions, option
trade-offs, pricing grounds and the current version. One provider and one sandbox merchant are
preset; there is no registration, multi-merchant, revenue split, escrow, refund management or
project management.

The model only handles natural-language extraction, clarification, option proposal and explanation.
Prices, feasibility checks, permissions, state transitions and retry policy are handled by the
program. Invalid model output must not reach confirmation or payment. The model never creates or
captures a payment.

## Architecture and operation

The front end calls FastAPI through the business API. The back end has four modules — requirements
and proposals, rule validation, quote versions, payments — sharing PostgreSQL; the rules module in
the architecture diagram is an internal backend module. Run locally first with a front-end dev
proxy; in deployment, same-origin reverse proxying minimises CORS configuration. Diagrams:
architecture.html and workflow.html.

PayPal integration starts with the REST Orders CAPTURE flow — explicit create, capture and query
operations. The Agent Toolkit is not a first-version dependency; if tool calling is added later, it
is restricted to proposal query and verification tools, while payments remain under human
confirmation and server-side state control. The client never submits the final payment amount; the
server reads it from the current confirmed quote.

The provider signs in with a single account and a server-side session; the client access token is
scoped to one requirement, and the server verifies ownership of every resource. Development uses
demo data; secrets live only in environment variables; the public repo keeps only the environment
template. Concrete endpoints, model contract and states: DEVELOPMENT.md.

## Data and transaction principles

Persist service rule versions, requirements and messages, candidate proposals, immutable quote
versions, payment attempts and order snapshots. Quote items keep message IDs and rule IDs; the
program validates that explainability references resolve. Amounts are integer minor units (cents);
the demo uses USD only.

Selecting an option creates a draft; the provider reviews; the client confirms. Requirement changes
create new drafts and supersede old confirmations. Once payment starts the version is locked and
must not change while the result is unknown; a paid order is read-only, and new services go into a
new requirement. A client cancel only means the interaction stopped; the server verifies before
deciding whether to unlock.

A successful payment must verify capture state, amount, currency, linked order and merchant. Create
and capture each use stable request identifiers; local unique constraints and transactions prevent
double execution. Timeouts enter a verifying state and query the original transaction; retry with
the original operation identifier only when the outcome is definitively incomplete. PayPal's support
and retention window for request identifiers varies by endpoint and must not be treated as a
permanent deduplication mechanism. The first version triggers recovery through the return page,
reopening the order and manual seller verification — no claim of unattended automatic
reconciliation.

## Schedule and cut order

After the scope upgrade, the core estimate is 88 hours plus a 12-hour submission buffer; the old
70-hour estimate no longer applies.

| Date (Beijing time) | Work | Hours | Done when |
|---|---|---:|---|
| Oct 30–31 | Interviews, rules, scaffolding, eval samples | 10 | Fixed service rules and five representative cases |
| Nov 1–2 | Data, permissions, manual options and quotes | 14 | Review and confirmation work without the model |
| Nov 3–4 | Requirement extraction, option generation, rule validation | 18 | Conflict cases yield a legal option or a clear no-solution |
| Nov 5–6 | PayPal sandbox, version locking, recovery | 18 | Successful payment and timeout recovery reproducible |
| Nov 7–8 | Option comparison, evidence links, change UX | 14 | A new user understands trade-offs and completes a transaction |
| Nov 9–10 | Evaluation, trial, fixes, materials | 14 | 20 cases and a clean-environment run record |
| Nov 11–12 | Freeze, record, submit | Buffer | Submission complete before the 12th, 20:00 |

When behind, cut in order: advanced service configuration, candidate option count, visual polish.
Constraint validation, evidence links, two-sided confirmation, real sandbox payment and state
recovery are always kept. If the payment loop is not done by November 6, stop adding product
capability.

## Acceptance and evaluation

pytest verifies business rules and state transitions; Playwright verifies the main user flow. The
20 fixed cases cover missing information, over-budget, unoffered capabilities, deadline conflicts
and requirement changes. Compare single-prompt generation against propose-then-validate using the
same inputs and service rules, three runs per case.

Record the generated-option violation rate, the final released violation rate, the feasible-option
ratio, no-solution identification, average and P95 latency, actual token usage and cost estimates.
Human review provides reference labels; rejecting everything is not high quality. The following must
pass: amounts cannot be overridden by the model, unauthorised requests are rejected, stale versions
cannot be paid, double clicks do not double-charge, timeouts are not misread as failures, paid
snapshots are immutable. Model evaluation and payment integration tests are recorded separately.

At least one real trial with recorded feedback. Fault demos may inject a lost capture response with
a test proxy, marked as a simulated fault; the payment itself still runs on the real sandbox.

## Video and submission

A 2 minute 40 second video: problem 20 s, conflict detection and two-option comparison 40 s, pricing
grounds and review 30 s, change confirmation 20 s, sandbox payment and recovery 30 s, actual
evaluation results 20 s. English, or English subtitles, published on YouTube, under three minutes.

Deliver the public repository with license, README, environment template, sandbox run guide, project
description, screenshots and video. MIT is the suggested license; dependency licenses checked before
release. The official deadline is recorded from current rules as 04:00 Beijing time on 13 November
2026; re-check the event page before submitting. Judging is five equal-weight criteria — technical
implementation, product design, potential impact, innovation, demo — carried over from the earlier
official-page verification; the four-item summary in REQUIREMENTS.md is not the development
baseline.

## Sources and next step

Competition rules: https://paypalaihackathon.devpost.com/rules

PayPal Orders: https://developer.paypal.com/api/rest/integration/orders-api/

PayPal idempotency: https://developer.paypal.com/api/rest/reference/idempotency/

Product, architecture and hour figures are this project's decisions; competition requirements carry
over the earlier verification record. Next step: start M0 per DEVELOPMENT.md — establish verifiable
rules and the manual closing loop first.
