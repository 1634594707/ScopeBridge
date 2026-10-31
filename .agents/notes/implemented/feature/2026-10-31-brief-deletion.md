# Agent Note: Sellers can delete an unpaid brief; a paid brief cannot be deleted at all

Status: implemented

## Problem

Briefs accumulated on the desk with no way to remove test entries or junk. Deletion also has a hard
edge in the data model: `order_snapshots.requirement_id` is `FK ... RESTRICT`, because the paid
snapshot is the receipt for the money that moved. Any delete path has to respect that or fail.

## Decision

**`DELETE /api/requirements/{id}`, seller + CSRF, hard delete with one guard and one fixed order.**

- Guard: any existing `OrderSnapshot` for the requirement → `409 payment_completed` ("The order
  snapshot is the receipt and cannot be deleted"). No soft-delete variant: a paid brief must stay
  visible and auditable, and an unpaid one must leave no orphan rows behind.
- Order (children first, respecting `quote_versions.proposal_id → RESTRICT`): payment attempts →
  quote items → quote versions → proposals → requirement messages → the requirement. Done in
  `requirements/service.py: delete_for_seller` with explicit `delete()` statements so the DB-level
  RESTRICT edges can never be hit mid-cascade.
- Console UI: a trash control on each row opens an inline two-step confirm (Delete / Cancel — no
  `window.confirm`); success invalidates the `["requirements"]` list; the 409 renders as "Paid
  briefs cannot be deleted." next to the control.

## Alternatives considered

- **Soft delete (`deleted_at` column).** Strongest case: recoverable mistakes, and paid briefs
  could be "archived" instead of refused. Rejected: every list query in the app grows a filter
  forever, for a demo where the real need is removing test rows; and archiving a paid brief would
  still leave the receipt on the desk — the guard already expresses the invariant.
- **Cascade at the database level only** (`ON DELETE CASCADE` everywhere). Rejected: SQLite/PG
  cascades do not guarantee the row order that `quote_versions → proposals (RESTRICT)` needs; the
  explicit order is what makes the delete deterministic.

## Consequences

- Benefit: the desk stays clean; the payment-completed invariant is enforced where the data model
  already drew the line.
- Cost: hard delete destroys an unpaid brief's history (messages, proposals, quotes). That is the
  point — but it also means a stray click on an unpaid brief cannot be undone; the two-step confirm
  is the only brake.

## Verification

- `uv run pytest -q` 87 passed, including: delete of an unpaid brief (204 + 404 afterwards), 409
  `payment_completed` after a captured payment, anonymous delete → 401.
- Browser: seller deletes the freshly submitted E2E brief from the console; the row disappears and
  the counters drop; the seeded briefs stay untouched.
