# Agent Note: Payments lock the quote before calling PayPal; unknown results are only verified

Status: implemented

## Problem

PayPal Orders v2's "create → buyer approval → capture" is three independent steps; the capture
request may time out, its response may be dropped after the charge, and a successful browser return
may be a user-forged URL. Treating "the browser came back" or "HTTP 200" as paid produces two error
classes: money taken with no local order, or a locally paid order with no actual charge. In
addition, repeated clicks or repeated captures on the same quote would create two real charges.

## Decision

**Lock first, call second, verify last.** When payment starts, the quote moves from `CONFIRMED` to
`PAYMENT_LOCKED`, the `PaymentAttempt` is persisted as `CREATING` and committed, and only then does
the code call PayPal. Every external call happens after the transaction commits.

**The amount comes only from the server.** Order creation uses the confirmed quote's `total_minor`
and `currency`; the client request body has no amount field. After capture, `capture.amount.value`
and `currency_code` are compared verbatim against the quote; a mismatch enters `RECONCILING` and
never writes an order snapshot.

**Unknown results always enter `RECONCILING`.** Transport errors, 5xx and
`ORDER_ALREADY_CAPTURED` are never judged failures; instead the original order is queried at
PayPal: `COMPLETED` backfills the snapshot, `APPROVED` re-captures with the same
`PayPal-Request-Id`, and only `VOIDED`/`EXPIRED` is judged `FAILED` and unlocks the quote.

**Idempotency has a database backstop.** `idempotency_key`, `paypal_order_id` and
`paypal_capture_id` are each unique; at most one active attempt per quote, enforced by the partial
unique index `uq_payment_attempts_active_quote`; `OrderSnapshot.quote_version_id` is unique, and the
snapshot plus `PAID` commit in one transaction. The same key on a different quote returns
`409 idempotency_conflict`.

**A buyer cancel is not a refund signal.** `cancel_url` only returns to the status page and does not
unlock; the quote returns to `CONFIRMED` only after the server verifies a definitive "no successful
capture".

## Alternatives considered

1. **Trust the browser-returned `?paypal=return` parameter directly**. Strongest case: least
   implementation work, smooth UX, and PayPal really does send the buyer back there. Rejected: the
   return URL is client-forgeable, the server would do no amount or state verification, and a
   "charged but response lost" capture could not be handled.
2. **Client submits the amount; the server creates the order as told**. Strongest case: the front
   end could show arbitrary add-ons and discounts. Rejected: violates "amounts come only from the
   rules layer", and one tampered request changes the charge.
3. **Treat `PayPal-Request-Id` as a permanent deduplication mechanism**. Strongest case: PayPal
   officially supports replaying the same request to the same result, so no local unique key would
   be needed in theory. Rejected: the retention window for request identifiers varies by endpoint
   and cannot be treated as a long-term uniqueness guarantee; local unique constraints are the final
   line of defence.
4. **Automatically retry the capture after a timeout**. Strongest case: most timeouts are network
   jitter and retries raise the success rate. Rejected: capture has a real side effect, and blind
   retries can cause a second charge; query first, then decide — that is this design's only path.
5. **Unlock the quote when the client cancels**. Strongest case: a user who does not want to pay
   should immediately be able to edit again. Rejected: cancel is an interaction event and proves
   nothing about charges; unlocking would let the same version be paid again in an unknown state.

## Consequences

- Benefit: the paid state can only arise from "a server-queried COMPLETED capture + matching
  amount"; duplicate clicks, duplicate captures and lost responses all have defined behaviour; every
  successful payment has an immutable snapshot.
- Cost: a quote can stay in `PAYMENT_LOCKED` for a long time, requiring the seller to press
  "Verify with PayPal" in the console or the buyer to refresh the payment status page; there is no
  unattended reconciliation job.
- Known limitation: sandbox buyer approval must be done by hand; without `PAYPAL_MERCHANT_ID` only
  amount and currency are verified, not the payee; no refunds, partial captures or instalments.
- Before any production integration: webhook verification, a scheduled reconciliation job and a
  refund state machine must be added, with a new note linked to this page.

## Verification

- `backend/tests/test_api_payment.py`: locking and the approve link, duplicate-key reuse, capture
  writes exactly one snapshot, amount mismatch stays `RECONCILING`, lost response recovered by
  verification, declined capture unlocks and allows retry, cross-quote key conflict, unconfirmed
  quotes cannot be paid, cross-tenant client token 404.
- Real sandbox (2026-10-30): created order `52192821KS579122X` returned an approve link; capturing
  before approval returned `not_approved` with the quote still `PAYMENT_LOCKED`; the seller
  verification endpoint returned `AWAITING_APPROVAL`.
