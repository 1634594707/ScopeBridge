# Agent Note: The portal-token authorisation path is deleted outright

Status: implemented

## Problem

Two authorisation paths coexisted by design: cookie sessions for the seller and an
`X-Customer-Token` header (resolving a hashed, per-requirement portal token) for the client. The
token's only job was to stand in for an identity the client did not have. Once clients hold
accounts (see [2026-10-31-two-sided-accounts](../feature/2026-10-31-two-sided-accounts.md)), the
token stops adding security and starts adding a second path to keep alive — the exact situation the
deps docstring had warned about since the beginning.

## Decision

**Delete the mechanism, not just the route guard.** `requirements.portal_token_hash` is dropped in
migration `a4c1e7d20b53`; `require_customer`, `CUSTOMER_HEADER`, `load_for_portal` and the
`X-Customer-Token` CORS entry are removed; the frontend loses `lib/customerToken.ts` (including the
never-called `forgetPortalToken` — the token outlived the tab session because nothing cleared it)
and the `customer: true` request channel. Portal routes take the requirement id in the path and
authorise via session + ownership; `PaymentOut` carries `requirement_id` so the pay page can link
back without client-side storage. Portal routes are:
`GET /api/portal/briefs`, `GET /api/portal/{requirement_id}`,
`POST /api/portal/{requirement_id}/messages`,
`POST /api/portal/{requirement_id}/proposals/{id}/select`,
`POST /api/portal/{requirement_id}/quotes/{id}/confirm`,
`POST /api/portal/{requirement_id}/quotes/{id}/payment-attempts`,
`GET|POST /api/portal/payments/{id}(/capture)`.

## Alternatives considered

- **Keep the column and routes, ignore them.** Strongest case: old `/r/:token` links keep working.
  Rejected: dead authorisation surface is worse than broken old links; "single path, no fallback"
  is an iron rule of this repo, and a dormant token column is a fallback waiting to be re-armed.

## Consequences

- Benefit: one authorisation story (session + ownership), fewer headers, no sessionStorage state to
  clear, and the seed no longer writes `data/demo_portal.txt`.
- Cost: any previously shared `/r/:token` link is dead; open `data/demo_portal.txt` files in old
  notes and screenshots refer to a mechanism that no longer exists.

## Verification

- `rg "portal_token|X-Customer|customerToken"` over `backend/app` and `frontend/src` returns only
  historical notes; `uv run pytest -q` 87 passed (token-flow tests rewritten to client sessions);
  `pnpm exec vite build` passes.
