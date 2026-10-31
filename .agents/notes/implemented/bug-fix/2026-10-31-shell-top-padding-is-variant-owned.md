# Agent Note: The fixed top bar owns 56px of `main` on public pages — `lg:pt-0` belongs to the seller variant only

Status: implemented

## Problem

On public pages at desktop width (≥1024px), the first line of content was rendered under the fixed
top bar: the "Client intake" eyebrow on `/start` showed its top half clipped behind the
`ScopeBridge / Price list / Seller console` header. Every public page starts with a `PageHeader`, so
all of them lost the same slice.

Root cause — one padding class served two masters:

- `TopBar` is `fixed inset-x-0 top-0 h-14` and, for the `public` variant, visible at **every**
  viewport width (`lg:hidden` applies to the `seller` variant only).
- `AppShell` gave `main` an unconditional `pt-14 lg:pt-0`. The `lg:pt-0` reset was written for the
  seller layout, where the top bar disappears at `lg` and the fixed left rail takes over — there the
  content may start at y=0. Applied to the public layout, the reset cancelled the only offset that
  keeps content below the fixed bar.

## Decision

**`main`'s top padding is owned by the variant that owns the chrome**: `pt-14` unconditionally;
`lg:pt-0` travels inside the seller-branch classes.

```tsx
<main className={cn("pt-14", sellerChrome ? "lg:pl-[236px] lg:pt-0" : "")}>
```

where `sellerChrome = variant === "seller" || session.data?.account?.role === "SELLER"` (a client variant exists beside it since [2026-10-31-two-sided-accounts](../feature/2026-10-31-two-sided-accounts.md)) — the selector of
"which chrome is active" moved to the session in
[2026-10-31-seller-rail-follows-session](2026-10-31-seller-rail-follows-session.md); the pairing
below is unchanged.

The invariant: the fixed top bar always covers the first 56px of the viewport on the public variant,
so public `main` must keep `pt-14` at every width. Only the seller variant may drop the offset at
`lg`, because that is exactly the width where `TopBar` renders `lg:hidden`.

## Alternatives considered

- **Make `TopBar` `sticky` so content flows below it naturally.** Strongest case: removes the
  padding pairing entirely and cannot regress. Rejected: the seller variant needs the bar *gone* at
  `lg` while the rail stays fixed, and a sticky bar occupies layout space at every width — the seller
  geometry would change for no visible gain, and the paper/backdrop layering of the fixed header is
  tuned against an overlay.
- **Push the offset down to each page** (padding on `PageHeader` or per-page roots). Rejected: it
  spreads one layout invariant across every page; `AppShell` owns the chrome, so it owns the offset.

## Consequences

- Benefit: public pages start below the bar at every width; verified on `/start` at 1440×900 — the
  eyebrow renders fully.
- Cost: the pairing "TopBar visible ↔ `pt-14`, TopBar hidden ↔ `lg:pt-0`" now lives across the
  `TopBar` variant logic and the `main` className. Changing either half alone reintroduces the
  overlap; the invariant above is the thing to preserve.
- The seller variant renders with exactly the same classes as before (they only moved into its
  branch), so seller layout is unchanged.

## Verification

- Before: user-reported screenshot at desktop width showing "CLIENT INTAKE" half-clipped under the
  top bar on `/start`.
- After: `cd frontend && pnpm exec tsc -b` and `pnpm exec vite build` pass; `/start` served by Vite
  preview at 1440×900 renders the eyebrow fully below the fixed bar.
