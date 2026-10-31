# Agent Note: The seller rail follows the session, not the route

Status: implemented

## Problem

The seller rail (Console / New brief / Price list / sign-in state) rendered only on seller-variant
routes (`/console`, `/requirements/:id`, `/quotes/:id`). Its own nav items point at public-shell
pages: clicking "New brief" lands on `/start` and "Price list" on `/rules` — and there the rail
disappears, replaced by the client-facing top bar. The seller is dropped out of the desk chrome by
the desk's own navigation (reported: "侧边栏只有 console 页面看得到,其他看不到").

## Decision

**Chrome selection reads the session, not the route.** `AppShell` computes

```tsx
const sellerChrome = variant === "seller" || session.data?.account?.role === "SELLER";
```

and one flag drives all three halves of the shell: rail rendered, which top bar renders
(`RoleTopBar`, `lg:hidden` under role chrome, or the anonymous `PublicTopBar`), and `main`'s
`lg:pl-[236px] lg:pt-0` offset (see
[2026-10-31-shell-top-padding-is-variant-owned](2026-10-31-shell-top-padding-is-variant-owned.md)
for the padding pairing). The session shape and the role check moved with
[2026-10-31-two-sided-accounts](../feature/2026-10-31-two-sided-accounts.md): clients now get a
rail of their own, selected the same way.

- A signed-in seller keeps the rail on every page, including the client portal `/r/:token` and
  `/pay/:id` — which is what the presenter wants when demoing the client's confirmation flow.
- Anonymous visitors always get the client-facing top bar. Real clients never hold a seller session,
  so the intake form, portal and payment pages stay clean for them.

## Alternatives considered

- **Move `/start` and `/rules` into the seller layout permanently.** Strongest case: zero
  conditional logic and no load-time flash. Rejected: both pages are client-facing entry points (the
  landing page targets anonymous clients); they would carry seller nav to people who cannot use it,
  and the Console link bounces them into the sign-in wall.
- **Keep the two shells and treat the switch as intentional role separation.** Strongest case: the
  audience split stays visually loud. Rejected: the switch happens exactly on the rail's own links,
  so it reads as breakage, not design.
- **Persist the session in `sessionStorage` to kill the hard-load flash.** Rejected for now:
  client-side navigation renders the rail instantly from the react-query cache (`staleTime` 30s,
  stale-while-refetch), so the flash only affects hard loads of public pages while signed in — one
  top-bar→rail swap after the session resolves. A storage copy would instead risk showing the rail
  to a visitor who has actually signed out.

## Consequences

- Benefit: one navigation surface for the signed-in seller across the whole app; the rail's own
  links no longer change the shell.
- Cost: every public page view now issues `GET /api/session` (a single 401 for anonymous visitors,
  `retry: false`); and a signed-in hard load of a public page swaps chrome once the session
  resolves. If either ever matters, the storage-persisted variant above is the recorded escape.
- Seller routes render the seller shell only for a confirmed session — anonymous visits redirect to
  `/signin` (see [2026-10-31-anonymous-never-sees-seller-chrome](../feature/2026-10-31-anonymous-never-sees-seller-chrome.md));
  the `variant === "seller"` arm remains as the short-circuit behind that gate.

## Verification

- Signed in through `/signin` with the demo account, then rail → "New brief": `/start` renders the
  rail (New brief active) with no top bar at 1440×900 and the "Client intake" eyebrow fully visible;
  rail → "Price list": `/rules` keeps the rail (complementary landmark visible, three nav links).
- Anonymous baseline: `/start` at 1440×900 still renders the top bar without the rail (screenshot
  from the padding fix earlier the same day).
- `cd frontend && pnpm exec tsc -b` and `pnpm exec vite build` pass; backend untouched.
