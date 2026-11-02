# ScopeBridge — Formal Proposal

AI-assisted service negotiation and closing assistant

Version 3.0 · 30 October 2026 · Independent developer · Design prior to implementation

## 1. Project summary

ScopeBridge is an AI service-negotiation and closing assistant for freelance web designers. It helps
a client and a service provider turn a vague, possibly conflicting request into an executable
engagement that passes rule validation and is confirmed by both sides, followed by a PayPal sandbox
payment.

The project concentrates on three capabilities: generating feasible options under budget and
deadline constraints, building a traceable relationship between requirements and pricing grounds,
and recovering transaction state when a payment result is unknown. The AI understands, proposes and
explains; the program sets prices, rules, permissions and state; both sides keep the final say.

The stack is React + TypeScript on the front end, Python + FastAPI on the back end, and PostgreSQL.
Planning for a single developer: roughly 88 hours of core work plus a 12-hour submission buffer.
Deliverables are a reproducible end-to-end prototype, evaluation evidence and complete submission
materials. This proposal is a design document; expected value is never presented as a verified
result.

## 2. Name and positioning

English name: **ScopeBridge**. Chinese name: **合意桥** (agreement bridge). Product description:
**AI service negotiation and closing assistant**.

"Scope" is the service scope; "Bridge" is the connection from an expressed need to mutual
agreement and transaction execution. The Chinese name emphasises that both sides reach a clear,
shared understanding of what will be delivered. The name contains no PayPal branding and implies no
official product relationship; it is used as this project's name, and trademark, name-collision and
domain availability are to be checked before any public release.

English one-liner: ScopeBridge helps freelancers turn ambiguous client requests into feasible,
traceable service agreements and human-approved PayPal sandbox payments.

## 3. Target users and problem hypothesis

The primary user is an individual freelancer providing website design services; the other side is a
small business that needs a website. The first version demonstrates with a single provider and a
coffee-shop client, without claiming that this segment is market-validated.

| User | Unvalidated problem | What the product provides |
|---|---|---|
| Client | Cannot tell whether budget, features and deadline can hold together | Feasible options, trade-offs and explicit prices |
| Provider | Repeats scope explanations; add-ons destabilise quotes | Linked evidence, version comparison, review and confirmation |
| Both | Payments hard to match with verbal agreements | Payment bound to the confirmed version, with an order snapshot |

During the starting phase, interview three potential users about their most recent quoting
experience and record concrete instances of back-and-forth, missed conditions and add-on requests.
At least one external trial must happen before launch. Actual feedback decides the value narrative;
no claim of improved close rates or reduced disputes is made in advance.

## 4. Product goals and competitive strategy

The project does not use the number of technical components as proof of sophistication. The
hackathon demonstration focuses on one observable decision process: an infeasible original request,
the system explaining the conflict and proposing rule-constrained alternatives, both sides
confirming, and a real payment.

| Capability | How it is implemented | Demonstration evidence |
|---|---|---|
| Option generation under constraints | Extract conditions, propose candidates, program verification | Over-budget and deadline-conflict cases |
| Traceable pricing grounds | Quote items link to messages and rule versions | Click a fee to see the originating request and rule |
| Change and payment consistency | Version confirmation, payment locking, transaction recovery | Add-on request and lost-capture-response cases |

Monetisation is a post-competition hypothesis: if trials show the product saves quoting
communication cost, a monthly subscription or usage-based pricing could be explored. The
competition version charges no platform fee and takes no payment split. Before widening the user
base, validate real usage frequency, model cost and willingness to pay.

## 5. Core scenario and business flow

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

[Open the business workflow diagram](workflow.html)

The diagram shows the closing main line plus the change and unknown-payment-result branches.
Missing information stays in clarification, no feasible solution goes to a human, a failed review
stays a draft — none of these may enter payment directly.

## 6. Feature scope and page design

The first version contains four page groups: service configuration, client requirement with option
comparison, provider review, and order detail. Core pages foreground unconfirmed conditions, option
trade-offs, pricing grounds and the current version. One provider and one sandbox merchant are
preset; there is no registration, multi-merchant, revenue split, escrow, refund management or
project management.

The model only handles natural-language extraction, clarification, option proposal and explanation.
Prices, feasibility checks, permissions, state transitions and retry policy are handled by the
program. Invalid model output must not reach confirmation or payment. The model never creates or
captures a payment.

| Page | Core content | Done when |
|---|---|---|
| Service configuration | Prices, capabilities, revision rounds, lead-time conditions | Configuration is versioned; old quotes never change with new rules |
| Requirement and comparison | Original text, clarifications, at most two options, budget delta | Unsatisfied conditions are explainable; options are selectable |
| Review and confirmation | Fee sources, delivery scope, version diff | Provider reviews, then the client confirms that exact version |
| Order detail | Payment progress, verification entry, service snapshot | Unknown state is explicit; paid snapshots are read-only |

The first version charges only the currently agreed service stage; future stages are described but
never billed without confirmation.

## 7. Architecture and technology choices

The stack is fixed: React + TypeScript + Vite front end, Python + FastAPI back end, Pydantic
validation, SQLAlchemy + Alembic for data access and migrations, PostgreSQL storage. The back end is
one process with business modules and an explicit state machine. The model uses one provider with
structured output; the exact model is pinned with small samples, and model and prompt versions are
frozen before evaluation. No Go, no multi-agent frameworks, no vector databases, no message queues,
no extra microservices.

The front end calls FastAPI through the business API. The back end has four modules — requirements
and proposals, rule validation, quote versions, payments — sharing PostgreSQL; the rules module in
the architecture diagram is an internal backend module. Run locally first with a front-end dev
proxy; in deployment, same-origin reverse proxying minimises CORS configuration.

PayPal integration starts with the REST Orders CAPTURE flow — explicit create, capture and query
operations. The Agent Toolkit is not a first-version dependency; if tool calling is added later, it
is restricted to proposal query and verification tools, while payments remain under human
confirmation and server-side state control. The client never submits the final payment amount; the
server reads it from the current confirmed quote.

The provider signs in with a single account and a server-side session; the client access token is
scoped to one requirement, and the server verifies ownership of every resource. Development uses
demo data; secrets live only in environment variables; the public repo keeps only the environment
template. Detailed conventions follow in later sections.

[Open the technical architecture diagram](architecture.html)

Architecture arrows mean call or read/write dependency; responses return along the call chain. Rule
validation is an internal backend module, not a separate deployment; the model and PayPal are
external services.

## 8. AI option generation and rule validation

The pipeline is, in order: requirement extraction, clarification of gaps, candidate proposal,
structural validation, business-rule validation, human review. Candidates must not fabricate
discounts, capabilities or delivery promises; rule-violating options never pass toward payment. The
program checks that source IDs exist; whether references are faithful to the original text is
verified by human review during sample evaluation.

Model input contains only the current requirement, the permitted rules and necessary context —
never secrets or payment credentials. Client text is treated as data; instructions embedded in it
cannot modify rules, tool permissions or amounts. If the model is unavailable, the requirement is
preserved and a clearly labelled manual quote is allowed, never disguised as AI-generated.

Model output is `requirement_fields`, `missing_questions`, `candidate_scopes`,
`source_message_ids`. Price fields, even when present, are never used as business amounts. The
validator returns `feasible`, `violations`, `computed_items`, `total_minor`, `currency`. Unknown
rules, invented sources, negative quantities, illegal currencies or missing conditions are all
rejected.

## 9. Data design and consistency

| Entity | Core fields and constraints |
|---|---|
| ServiceRuleVersion | Immutable rule JSON, currency, prices, capabilities, lead-time conditions |
| Requirement and Message | Ownership, original messages, budget, dates, asset conditions, revision number |
| Proposal | Requirement revision, rule version, inclusions, exclusions, trade-offs, validation result |
| QuoteVersion and QuoteItem | Version, amounts, message and rule references, review/confirmation times, state |
| PaymentAttempt | Quote ID, operation request identifier, PayPal order ID, capture ID, state |
| OrderSnapshot | Snapshot of the paid quote, payment linkage, created time; unique per successful payment |

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

## 10. API and access control

| Method and path | Purpose and permission |
|---|---|
| POST /api/session | Provider sign-in; attempts limited |
| GET /api/service-rules | Read quotable rules |
| POST /api/requirements | Create a client requirement and its restricted access |
| POST /api/requirements/{id}/messages | Append original text with expected_revision |
| POST /api/requirements/{id}/proposals | Generate and validate at most two options |
| POST /api/requirements/{id}/quotes | Draft a quote from a feasible option |
| POST /api/quotes/{id}/review | Provider only; review the current version |
| POST /api/quotes/{id}/confirm | Client confirms a reviewed, unexpired version |
| POST /api/quotes/{id}/payment-attempts | Lock the confirmed version; create or return the existing payment |
| POST /api/payments/{id}/capture | Capture after verifying ownership and quote state |
| POST /api/payments/{id}/reconcile | Query the original payment and update local state |
| GET /api/orders/{id} | Read orders and snapshots within the authorised scope |

Payment writes carry an `Idempotency-Key`; the same key with a different body is a conflict. The
backend persists business keys mapped to PayPal request identifiers, stored separately for create
and capture. Concurrent edits use expected_revision; conflicts return 409. Unauthenticated returns
401, lacking resource permission 403, invalid input 422. Unknown external results return a
recoverable in-progress state; the front end must never treat that as paid. Cookie-session writes
add CSRF protection.

## 11. State machines and payment recovery

Quote: DRAFT → REVIEWED → CONFIRMED → PAYMENT_LOCKED → PAID. Review edits produce a new draft;
changes before payment starts mark the old version SUPERSEDED. PAYMENT_LOCKED unlocks only after the
server verifies that no successful capture exists and the old operation cannot continue; when that
cannot be judged, the lock is kept for verification.

Payment: CREATING → AWAITING_APPROVAL → CAPTURING → COMPLETED. Any unknown external outcome enters
RECONCILING; if the query shows completed, write the order; if definitively awaiting approval,
resume the approval flow; only a definitive failure enters FAILED. A client cancel is recorded as an
interaction event and does not by itself release the payment lock.

At most one active payment attempt per quote; PayPal order ID and capture ID are each unique;
COMPLETED and the order snapshot are written in one transaction. If a database failure happens
after the external charge, the next verification backfills the local record. A completed state is
never overwritten by an older query result.

PayPal runs with intent=CAPTURE. Buyer approval, server capture and local bookkeeping are distinct
steps; a successful browser return is not by itself evidence of payment. External network calls
must never be wrapped in a long database lock: commit the active payment record first, then call
out, handling concurrency and recovery with state and unique constraints.

## 12. Implementation plan and milestones

Core effort estimate is 88 hours, plus roughly 12 hours of submission buffer.

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

- [ ] M0: five samples, service rules, repo structure, environment template, health check. Acceptance:
      front end, back end and database connected; secrets not tracked by Git.
- [ ] M1: pure-function price and feasibility validator. Acceptance: three pages = 70000 cents, a
      50000 budget does not pass, single-page external link vs on-site ordering clearly distinguished.
- [ ] M2: manual draft, review, confirmation, ownership permissions, version conflicts. Acceptance:
      unreviewed, unauthorised or stale versions cannot be confirmed.
- [ ] M3: model extraction, candidate options, evidence mapping. Acceptance: invalid output never
      reaches payment; every reference traceable; no-solution goes to a human.
- [ ] M4: real sandbox create, capture and recovery. Acceptance: duplicate requests, client cancel,
      lost capture response, database backfill each covered.
- [ ] M5: comparison, diff and order pages done; 20-case evaluation run; user trial conducted.
- [ ] M6: clean-environment reproduction, video, license and submission materials. Acceptance: every
      outward-facing metric maps to a test record.

After each milestone, record changes, verified items and open items; fix failures before moving on.
At the time of writing, no milestone is complete.

Implementation status on 2026-11-02: M0–M4 code complete; M5 code complete except the real user trial;
M6 pending. The trial has not been run and this document does not record one.

## 13. Acceptance criteria and evaluation method

pytest verifies business rules, state transitions and the API; the browser flow is covered by the
manual demo script in this build (Playwright is not implemented). The 20 fixed cases cover missing
information, over-budget, unoffered capabilities, deadline conflicts and requirement changes.
Compare single-prompt generation against propose-then-validate using the same inputs and service
rules; the recorded build has one run per case, recorded as a deviation in `DEVELOPMENT.md`.

Record the generated-option violation rate, the final released violation rate, the feasible-option
ratio, no-solution identification, average and P95 latency, actual token usage and cost estimates.
Human review provides reference labels; rejecting everything is not high quality. The following must
pass: amounts cannot be overridden by the model, unauthorised requests are rejected, stale versions
cannot be paid, double clicks do not double-charge, timeouts are not misread as failures, paid
snapshots are immutable. Model evaluation and payment integration tests are recorded separately.

At least one real trial with recorded feedback. Fault demos may inject a lost capture response with
a test proxy, marked as a simulated fault; the payment itself still runs on the real sandbox.

All critical payment and permission tests must pass; the fixed eval set targets zero final released
violations — that target describes the test set only, not a production safety guarantee. Also report
the available-option ratio on solvable cases, so blanket rejection cannot score well. All
performance and cost numbers are published as measured; unmeasured data is labelled unmeasured.

Evaluation evidence keeps case versions, model versions, prompt versions, inputs and outputs, rule
verdicts and human review records. Normal closing, requirement change, duplicate operation, cancel,
timeout and verification recovery must be reproducible from the run instructions.

## 14. Cost and risk management

Spending comes mainly from model calls, optional hosting and a domain. The first version runs
locally; no training resources or extra infrastructure are bought. Model experiments start with
small samples and a billing check before scaling to the full evaluation; request volume and actual
cost are recorded, with account spending limits and application rate limits configured. No fake
total price is written before the model and hosting are chosen.

| Risk | Trigger signal | Response and completion requirement |
|---|---|---|
| Requirement lacks real value | Interviews cannot cite a concrete problem | Narrow the scenario, revise the problem statement, never invent user data |
| Model generates infeasible options | Over-budget, invented services or references | Rules reject; manual handling allowed; failed samples recorded |
| Duplicate or unknown payment | Timeout, refresh, double click | Persist operation identifiers, query the original transaction, lock the quote |
| Scope change breaks payment consistency | New version after confirmation | New version re-reviewed; no edits during payment |
| Schedule overrun | Payment not done by November 6 | Shrink scope in the cut order, freeze new capability |
| Demo environment not reproducible | Missing credentials or dependencies | Environment template, seed data, sandbox guide, clean-install verification |

If an online demo is published, model calls and demo-data writes must be limited so strangers
cannot drain the quota. The first version never touches real card numbers and never switches to
production payments.

## 15. Demo and submission checklist

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

| Deliverable | Acceptance requirement |
|---|---|
| Application and public source | One closing main line actually interactive, with license |
| Run and environment instructions | Locked dependencies, environment template, seed data, sandbox account guide |
| Evaluation report | 20-case results, baseline comparison, actual cost, failure analysis |
| Demo video | End-to-end operation, English or English subtitles, within the time limit |
| Project description and screenshots | Problem, users, highlights, technical implementation, known limitations |

All published material uses ScopeBridge / 合意桥 consistently. What judges see must match what is
delivered; unimplemented prototype ideas go into future directions.

## 16. Engineering conventions and first steps

Suggested layout: frontend/src, backend/app, backend/tests, evals, docs. Inside backend/app,
business files are grouped by requirements, proposals, quotes, payments — no premature service
split. Pick compatible, stable dependencies when starting and commit lock files; no unverified
`latest` versions.

The environment template includes DATABASE_URL, MODEL_API_KEY, MODEL_NAME, PAYPAL_CLIENT_ID,
PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL, APP_BASE_URL, SESSION_SECRET. The sandbox base URL is pinned
in a server-side allowlist. Startup commands are written into the root README once the scaffolding
exists; this document does not provide commands that do not exist yet.

Step one is M0: fix the demo rules, five representative cases and data seeds; set up the repo
structure and connect front end, back end and database. Then write rule tests first, implement
manual review and confirmation, and only then attach the model and the sandbox. Each stage advances
only after meeting its acceptance criteria.

## 17. References

Competition rules: https://paypalaihackathon.devpost.com/rules

PayPal Orders: https://developer.paypal.com/api/rest/integration/orders-api/

PayPal idempotency: https://developer.paypal.com/api/rest/reference/idempotency/

Competition timing and submission requirements carry over the verification record of 30 October
2026; re-check the official page before submitting. The product scope, architecture, hour estimates
and evaluation targets in this document are project design decisions; implementation must follow the
official API constraints and actual tests at development time.
