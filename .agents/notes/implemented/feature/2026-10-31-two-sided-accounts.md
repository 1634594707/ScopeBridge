# Agent Note: Both sides sign in — client accounts replace the anonymous portal link

Status: implemented

## Problem

The proposal (v3.0 §6/§7) deliberately shipped no registration: one seeded seller signed in, and
clients reached their brief through an unguessable per-requirement token. That left brief creation
open to anonymous submissions, and nothing on the record identified who did what. The product owner
called it on 2026-10-31: 甲方乙方都应该登录 — both parties should hold accounts, because
attribution to a signed-in identity is what makes the record auditable ("对账").

## Decision

**One account table, one session table, one sign-in page; the role decides what a request may
touch.**

- `users.role` (`SELLER` | `CLIENT`); the seeded operator is the only seller, clients register
  themselves (`POST /api/clients`, open registration, 409 on duplicate email).
- `seller_sessions` → `user_sessions`: the session mechanism was already user-generic; the rename
  makes the semantics true. Cookies (`sb_session`/`sb_csrf`) and the CSRF flow are unchanged and
  shared by both roles — one browser holds one session at a time.
- `GET /api/session` now answers `{account: {id, email, display_name, role}, csrf_token}` —
  a breaking shape change the frontend absorbed everywhere. A wrong-role sign-in is answered like a
  wrong password, so the endpoint never confirms which side an email belongs to.
- `requirements.client_id` (nullable for the legacy seed row, which the seed claims): intake
  (`POST /api/requirements`) requires a client session and owns the brief; every former
  `require_customer` portal route now requires a client session **plus an ownership check**
  (`load_for_client`, 403 on another client's brief; payments resolve ownership through
  attempt → requirement → `client_id`).
- Frontend: one `RoleLayout` gates both shells (loading → public spinner, 401 → `/signin`, role
  mismatch → the other role's home); `AppShell` picks SellerRail/ClientRail from the session role;
  `/signin` is one page with a Studio/Client seat toggle, the client seat containing a
  sign-in/register switch. Client pages: `/briefs` (dashboard) and `/briefs/:id` (the former
  `/r/:token` portal page).
- `PaymentOut` gained `requirement_id` so the pay page can link back to the brief without any
  client-side token storage.

## Alternatives considered

- **Keep the token mechanism and just gate intake behind the seller session** (smallest change).
  Strongest case: minutes of work, no migration. Rejected: it makes the studio type in every brief
  and leaves the client anonymous — the audit trail the owner asked for never materialises.
- **Separate `clients` table + separate client sessions.** Strongest case: role data never
  pollutes the seller table. Rejected: the session/CSRF/throttle machinery would be duplicated for
  zero behavioural gain; one `role` column keeps every existing check a one-line comparison.
- **Keep portal tokens as the URL key and add ownership checks on top.** Strongest case: existing
  links stay valid. Rejected: with identity-based access, an unguessable URL adds no security and
  keeps a second authorisation path alive — exactly the "two paths" the old deps docstring warned
  about.

## Consequences

- Benefit: every brief, message, confirmation and payment is attributable to a signed-in account;
  junk briefs require an account; the seeded demo flow survives (seed claims the legacy brief for
  the demo client).
- Cost: v3.0's "clients never sign in" is formally deviated (recorded in DEVELOPMENT.md); the demo
  script gained a sign-in step; `POST /api/requirements` without a client session is now 401 —
  every anonymous brief-creation path must go through `/signin`.
- Tests: two TestClients per flow (cookie jars are per-browser, one session cookie each);
  `tests/helpers.py` centralises seller/client browsers.

## Verification

- `uv run pytest -q` 87 passed, `uv run ruff check .` clean; `pnpm exec tsc -b` and `pnpm exec
  vite build` pass; migration `a4c1e7d20b53` applied and seed re-run on the real database.
- Browser: client registration → `/briefs` with the client rail → brief submission →
  `/briefs/:id`; seller sign-in → console; anonymous `/briefs` redirects to `/signin`; a signed-in
  seller is redirected off client pages and vice versa (route-level), cross-role API access 403
  (tests).
