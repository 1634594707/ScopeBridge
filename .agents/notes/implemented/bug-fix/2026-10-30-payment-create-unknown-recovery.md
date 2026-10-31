# Agent Note: When order creation has an unknown result, the quote must not stay stuck forever

Status: implemented

## Problem

When payment creation hit a network error, the `PaymentAttempt` entered `RECONCILING`, but PayPal
never returned an order id. The previous `reconcile()` did `return attempt` whenever
`not attempt.paypal_order_id`: the API returned 200, the state never changed, and the quote sat in
`PAYMENT_LOCKED` forever — impossible to pay and impossible to re-quote. This was a P0 finding in
review: an exception path that could not be walked to the end.

## Decision

**Retry the create first, then allow manual closing; both leave a trail.**

- `POST /api/payments/{id}/retry-create` (seller, CSRF): calls `create_order` again with exactly the
  same `PayPal-Request-Id` as the first attempt. PayPal deduplicates by request id, so this either
  returns the original order or genuinely creates the one that never happened. At most 2 retries
  (`retry_count` persisted); beyond that, `409 retry_limit`.
- `POST /api/payments/{id}/close` (seller, CSRF): the request body must carry `note` (at least 10
  characters after trimming) and `confirmed_no_order: true`; only then does the server mark the
  attempt `ABANDONED`, record `resolved_by / resolved_at / resolution_note`, and move the quote back
  from `PAYMENT_LOCKED` to `CONFIRMED`.
- `reconcile()` with no order id now returns `409 no_order_id` with `retry_count` attached, instead
  of pretending success.
- Only attempts in `RECONCILING` / `FAILED` without a capture id can be closed; anything already
  `PAID` or carrying a capture id is refused.

## Alternatives considered

1. **Unlock the quote directly and let the client start over**. Strongest case: simplest, the user
   continues immediately. Rejected: if PayPal actually created the order and the buyer then approved
   it, an unrecorded payment would exist; unlocking treats the unknown as unpaid.
2. **No retry limit — retry create forever**. Strongest case: most timeouts are transient network
   issues, so retries succeed often and human involvement is minimal. Rejected: persistent failure
   means a gateway or credential problem; unlimited retries only amplify latency and log noise and
   mask a systemic fault.
3. **Provide a "mark as paid" manual escape hatch**. Strongest case: the demo flow could always be
   walked to the end by hand. Rejected: writing `PAID` without PayPal-side evidence pollutes order
   snapshots and the evaluation basis; closing may only move toward "unpaid".
4. **Keep the state and only change the front-end copy**. Strongest case: zero backend risk.
   Rejected: the state machine would have no exit, and the problem would merely change from "the
   user cannot tell what happened" to "the user knows it is stuck".

## Consequences

- Benefit: every failure path out of the create stage has a defined exit; retries and closings both
  leave database traces that evaluation and audit can review; a quote can no longer get stuck
  silently.
- Cost: retries depend on PayPal's request-id deduplication window; if the window lapses, a second
  order may be created, and its new order id is written onto the same attempt (the old order was
  never shown an approve link, so the risk is sandbox-limited).
- Known limitation: closing is a human judgement; the server cannot independently prove "PayPal has
  no order". The rationale is therefore mandatory, and the UI states "unlocking does not refund,
  because nothing was charged".
- Before any production integration, webhook-based reconciliation should be added, demoting this
  kind of closing to a last resort.

## Verification

- `backend/tests/test_api_payment.py`: verification with no order id returns `409 no_order_id`;
  retry-create recovers to `AWAITING_APPROVAL` (`retry_count=1`); a second retry hits `409
  retry_limit`; closing without confirmation or rationale is refused with `422`; after closing the
  attempt is `ABANDONED` and the quote returns to `CONFIRMED`; retry with an existing order id is
  refused with `409 order_already_exists`.
- Migration `b9318d6cb37a`: `retry_count` with `server_default '0'`, new
  `resolved_by / resolved_at / resolution_note`, foreign key `fk_payment_attempts_resolved_by_users`
  (reversible).
- Security review (STRIDE, `senior-security`): the new endpoints all require a seller session +
  CSRF and verify ownership through `requirement.seller_id` (unauthorised returns 404); closing
  requires explicit confirmation plus a written rationale recorded in
  `resolved_by / resolved_at / resolution_note` (Repudiation); retry cap of 2 (DoS); responses
  return only PayPal order/capture ids, never tokens. Secret scanning: all 19 hits were integrity
  hashes in `pnpm-lock.yaml` and `skills-lock.json` misflagged by Twilio rules; no hits in source or
  `.env`.
