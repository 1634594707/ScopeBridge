# Agent Note: Anonymous visitors never see the seller chrome — seller routes redirect to the standalone sign-in

Status: implemented

## Problem

The anonymous experience mixed the marketing surface with the app: `/console` for a signed-out
visitor rendered the full seller shell — rail, nav, "Seller access / Sign in to the desk" — around
the "The desk is locked" wall, and the landing page's "Enter the seller console" led into that same
shell. Reported requirement: 未登录时展示 SaaS 介绍页,登录与应用不混用 — the signed-out visitor
should see the SaaS intro and a clean sign-in page, never the desk chrome.

## Decision

**The seller shell mounts only on a confirmed session.** `SellerLayout` in `App.tsx` now gates the
`AppShell` itself (both role gates since share one `RoleLayout` — see
[2026-10-31-two-sided-accounts](2026-10-31-two-sided-accounts.md) — and a signed-in account of the
other role is redirected to its own home):

- session loading → neutral spinner inside the public shell (no rail);
- 401 → `<Navigate to="/signin" replace />`;
- other errors → an error message inside the public shell (fail fast; an unknown state never
  masquerades as "please sign in");
- confirmed seller → seller `AppShell` + `<Outlet />`.

`RequireSeller` — the in-shell "The desk is locked" wall — is deleted; the wall was the mixing
point. After sign-in the existing flow lands on `/console`. Client-facing surfaces stay public: the
intro `/`, the intake `/start`, the price list `/rules`, and the token-scoped `/r/:token` and
`/pay/:id` (clients never sign in — they hold a private link).

## Alternatives considered

- **Keep the locked wall but restyle it.** Strongest case: no routing change, sign-in intent stays
  visible in place. Rejected: it still shows the seller rail and nav to people who cannot use them —
  the mixing is the complaint.
- **Gate `/start` and `/rules` behind sign-in too.** Rejected: the intake form is the client's entry
  point and clients never sign in; hiding it breaks the lead flow the intro page advertises.
- **Redirect non-401 failures to `/signin` as well.** Rejected: an API outage would read as "please
  sign in", masking the real cause; only 401 proves the visitor is unsigned.

## Consequences

- Benefit: signed-out visitors see the SaaS intro and the standalone sign-in page only; the desk
  exists exclusively behind the session.
- Benefit: session expiry while on a seller route self-heals — the next 401 flips the route to
  `/signin` instead of showing a wall inside a stale shell.
- Cost: a hard load of a seller route while signed in flashes the public-shell spinner before the
  desk mounts (the same session-fetch tradeoff recorded in
  [2026-10-31-seller-rail-follows-session](../bug-fix/2026-10-31-seller-rail-follows-session.md)).
- The rail's signed-out branch ("Seller access / Sign in to the desk") becomes defensive-only — it
  can flash during the sign-out cache removal — and is kept so the rail never renders an empty
  identity block.

## Verification

- Anonymous reload of `/console` → redirected to `/signin` (public shell, no rail), screenshot;
- signing in lands on `/console` with the rail visible; the landing `/` intro is unchanged;
- `cd frontend && pnpm exec tsc -b` and `pnpm exec vite build` pass.
