# Agent Note: The seller rail gets a real sign-out; the anonymous rail block says "Seller access"

Status: implemented

## Problem

A signed-in seller could never end a session: the rail only offered "switch account", which merely
navigates to `/signin`. The server side was already complete — `DELETE /api/session` revokes the
row and clears both cookies — and `api.signOut()` existed in the frontend, unwired. The closest
thing to sign-out was signing in again with different credentials.

While verifying the anonymous experience, the rail's bottom block also read "Signed in" for
visitors who are not signed in (anonymous `/console` renders the seller shell with the locked wall,
so the block was visible with the wrong label).

## Decision

**The rail's signed-in block carries an explicit `sign out` action next to `switch account`.**
Clicking it:

1. calls `DELETE /api/session`; a 401 counts as "already signed out server-side" and still proceeds
   — any other failure surfaces "Sign out failed…" inline instead of pretending success (fail fast,
   no silent degradation);
2. on success, **removes** the `["session"]` query cache rather than merely invalidating it, so the
   shell flips to the client-facing top bar immediately;
3. navigates to `/` — the anonymous home.

The block label is now `seller ? "Signed in" : "Seller access"`.

## Alternatives considered

- **Land on `/signin` after sign-out.** Strongest case: the most common next step is signing in as
  someone else. Rejected: `/` is the anonymous home and shows exactly what a signed-out visitor
  sees; `/signin` stays one click away through "switch account".
- **`invalidateQueries` instead of `removeQueries`.** Strongest case: invalidation is the idiomatic
  react-query move. Rejected: a refetch keeps the old seller data rendered for a beat, so the rail
  would linger on public pages after the server already ended the session; removal drops the data
  at once and the next mount refetches from a clean slate.
- **A sign-out item in the below-`lg` top bar.** Rejected for now: the top bar carries navigation
  only, and the signed-in identity/sign-out pair already lives together in the rail; below `lg`
  there is currently no sign-out surface, recorded here as the known gap.

## Consequences

- Benefit: sessions can actually be ended (server-side revoke plus cookie clear), which is also the
  natural way to inspect the anonymous experience. The client rail gained the same control when
  accounts went two-sided ([2026-10-31-two-sided-accounts](2026-10-31-two-sided-accounts.md));
  `DELETE /api/session` is role-agnostic.
- Cost: sign-out is reachable only where the rail is (`lg` and up, seller chrome); the below-`lg`
  gap above.
- The `Seller access` fallback label is defensive-only since
  [2026-10-31-anonymous-never-sees-seller-chrome](2026-10-31-anonymous-never-sees-seller-chrome.md):
  seller routes redirect before the rail can render signed-out.
- The 401-tolerant path means a stale tab can still clean itself up after the session expired.

## Verification

- `cd frontend && pnpm exec tsc -b` and `pnpm exec vite build` pass.
- Browser (1440×900, Vite preview): signed in → click "sign out" → lands on `/` with the anonymous
  top bar and no rail; anonymous `/console` shows "The desk is locked" with the rail block now
  reading "Seller access / Sign in to the desk".
