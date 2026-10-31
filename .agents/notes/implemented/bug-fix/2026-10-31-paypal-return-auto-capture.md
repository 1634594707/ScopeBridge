# Agent Note: PayPal's return redirect rewrites the query string, so the auto-capture marker must be PayPal's own parameters

Status: implemented

## Problem

The advertised happy path is "PayPal returns you to `/pay/<id>`, which confirms the payment
automatically". In a recorded end-to-end sandbox run (2026-10-31, order `4DK256612F564790L`), the
buyer approved in PayPal ("Complete Purchase" → "Thanks for using PayPal") and PayPal redirected
back to

```
http://127.0.0.1:4173/pay/7cb2ba0e-…?token=4DK256612F564790L&PayerID=LSHM7VR4TJFWS
```

but the page stayed on the "AWAITING APPROVAL / Continue to PayPal" card forever. The backend log
shows only `GET /api/portal/payments/…` after the return — no capture call ever arrived — and the
database kept the attempt in `AWAITING_APPROVAL` with the quote in `PAYMENT_LOCKED`.

Root cause, two halves that only break in combination:

- `backend/app/payments/service.py` builds `return_url = f"{base}/pay/{attempt.id}"` with no query
  string, and
- `frontend/src/pages/PayPage.tsx` gated the auto-capture effect on
  `params.get("paypal") === "return"` — a marker this URL never carries.

Even if the server had appended `?paypal=return`, PayPal constructs the buyer's return navigation
from its own query string (`token`, `PayerID`); relying on our marker surviving that rewrite is
guessing at PayPal's behaviour instead of observing it.

## Decision

**Detect the return by the parameters PayPal itself appends: `token` AND `PayerID` both present.**

`PayPage.tsx` now reads:

```ts
const returnedFromPaypal = params.has("token") && params.has("PayerID");
```

- `token` alone is NOT enough: PayPal also appends `token` when the buyer cancels and lands on the
  cancel URL, and a cancel must not trigger a capture.
- `PayerID` is only added on the approve-return navigation, so requiring both distinguishes "the
  buyer came back from approving" from every other way this page can load.
- The dead `paypal === "return"` check is removed rather than kept as a second accepted spelling:
  one event, one detection path.

## Alternatives considered

- **Append `?paypal=return` to the server-side return_url and keep the marker check**. Strongest
  case: it makes the intent explicit in the URL we control. Rejected: the marker's survival depends
  on how PayPal merges our query string with `token`/`PayerID`, which we cannot observe from our
  side until a redirect happens; the observed behaviour (fresh query string) says it would be
  dropped. Same class of failure, one step removed.
- **Auto-capture whenever the page loads and the attempt is `AWAITING_APPROVAL`**. Strongest case:
  no URL inspection at all. Rejected: a buyer who reopens the payment status page later (without
  having approved) would fire a capture against an unapproved order; the server answers
  `not_approved`, but the attempt then carries an avoidable error code and the page shows a
  confusing warning. Triggering should require evidence the buyer actually returned from PayPal.
- **Move the trigger server-side (webhook or polling job)**. Strongest case: no browser coupling at
  all. Rejected for this build: the project deliberately ships no webhooks and no unattended
  reconciliation; the seller-triggered "Verify with PayPal" reconcile endpoint already covers the
  stuck cases.

## Consequences

- Benefit: the demo's money shot — return → "Confirming the payment" → "Payment confirmed" with the
  frozen order summary — actually happens on return, with no manual click.
- Benefit: the cancel path is now explicit: `token` without `PayerID` is not treated as an
  approve-return, so cancelling cannot fire a capture.
- Cost: the trigger now depends on PayPal's redirect parameter contract (`token`, `PayerID`) rather
  than a marker we own. That contract is what PayPal documents for buyer-approval redirects and what
  the recorded sandbox run produced; if PayPal ever changes it, the visible failure is the same
  "AWAITING APPROVAL" page, and the seller-side reconcile path still resolves the payment.
- The "Confirm again" button (previously unreachable because it was also gated on the
  `paypal=return` marker) is now visible after a real return, which is exactly what the recovery
  demo needs: stop the API between approval and capture, fail the auto-capture, restart, confirm.

## Verification

- Recorded run before the fix: buyer approved, page stuck on "AWAITING APPROVAL", backend log shows
  no capture request, DB: attempt `AWAITING_APPROVAL`, quote `PAYMENT_LOCKED`, zero order snapshots.
- After the fix (same harness, fresh database): the return URL
  `/pay/<id>?token=…&PayerID=…` triggers the auto-capture; the page transitions
  AWAITING_APPROVAL → COMPLETED, the quote reaches `PAID`, and the order snapshot row is written in
  the same transaction.
- `cd frontend && pnpm exec tsc -b && pnpm exec vite build` pass; backend suite untouched
  (`uv run pytest -q` 78 passed, `uv run ruff check .` clean).
