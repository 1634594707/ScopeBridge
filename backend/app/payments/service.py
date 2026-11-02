"""Payment orchestration: lock, create, capture, reconcile, snapshot.

Order of operations is the whole design:
1. lock the quote and commit the attempt locally,
2. call PayPal,
3. record the outcome.

A transport failure therefore never loses the fact that money might have moved;
the attempt goes to RECONCILING and the quote stays locked until the server has
queried the original order.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, conflict, not_found, unprocessable
from app.payments.models import ACTIVE_STATUSES, OrderSnapshot, PaymentAttempt
from app.payments.schemas import AttentionPaymentOut, PaymentOut, SnapshotItemOut, SnapshotOut
from app.paypal import client as paypal
from app.quotes.models import QuoteVersion
from app.quotes.states import QuoteStatus
from app.requirements.models import Requirement
from app.requirements.service import CLOSED_STATUS, brief_is_closed

MAX_CREATE_RETRIES = 2
STALE_ATTEMPT_SECONDS = 120


def _now() -> datetime:
    return datetime.now(UTC)


def recover_stale_attempts(db: Session, *, older_than_seconds: int = STALE_ATTEMPT_SECONDS) -> int:
    """Park in-flight attempts whose process never wrote a result.

    A crash between the local commit and the PayPal response leaves CREATING or
    CAPTURING behind. The external outcome is unknown, so the attempt must move
    to RECONCILING; it is never guessed as failed or paid.
    """
    cutoff = _now() - timedelta(seconds=older_than_seconds)
    result = db.execute(
        update(PaymentAttempt)
        .where(
            PaymentAttempt.status.in_(("CREATING", "CAPTURING")),
            PaymentAttempt.updated_at < cutoff,
        )
        .values(
            status="RECONCILING",
            error_code="stale_timeout",
            error_detail="No PayPal result was recorded before the stale window closed.",
            updated_at=_now(),
        )
    )
    db.commit()
    return result.rowcount or 0


def _require_paypal_configured() -> None:
    settings = get_settings()
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise ApiError(
            503,
            "paypal_not_configured",
            "PayPal sandbox credentials are not configured. Set PAYPAL_CLIENT_ID and "
            "PAYPAL_CLIENT_SECRET in .env.",
        )


def start_payment(
    db: Session, requirement: Requirement, quote_id: UUID, idempotency_key: str
) -> PaymentAttempt:
    recover_stale_attempts(db)
    quote = db.get(QuoteVersion, quote_id)
    if quote is None or quote.requirement_id != requirement.id:
        raise not_found("Quote not found")

    replay = db.scalar(
        select(PaymentAttempt).where(PaymentAttempt.idempotency_key == idempotency_key)
    )
    if replay is not None:
        if replay.quote_version_id != quote.id:
            raise conflict(
                "idempotency_conflict",
                "This idempotency key was already used for a different quote.",
            )
        return replay

    active = db.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.quote_version_id == quote.id,
            PaymentAttempt.status.in_(ACTIVE_STATUSES),
        )
    )
    if active is not None:
        return active

    if brief_is_closed(db, requirement):
        raise conflict("brief_closed", "This brief is closed after payment.")
    if quote.status == QuoteStatus.PAID:
        raise conflict("already_paid", "This quote has already been paid.")
    if quote.status != QuoteStatus.CONFIRMED:
        raise conflict(
            "quote_not_payable",
            "Only a confirmed quote can be paid.",
            {"status": quote.status},
        )
    if quote.source_revision != requirement.revision:
        raise conflict(
            "revision_changed",
            "The brief changed after this quote was confirmed. Ask for a fresh quote.",
            {
                "quote_revision": quote.source_revision,
                "current_revision": requirement.revision,
            },
        )
    if quote.expires_at is not None and quote.expires_at <= _now():
        raise conflict("quote_expired", "This quote has expired. Ask for a fresh one.")

    _require_paypal_configured()

    attempt = PaymentAttempt(
        quote_version_id=quote.id,
        requirement_id=requirement.id,
        status="CREATING",
        idempotency_key=idempotency_key,
        amount_minor=quote.total_minor,
        currency=quote.currency,
    )
    locked = db.execute(
        update(QuoteVersion)
        .where(QuoteVersion.id == quote.id, QuoteVersion.status == QuoteStatus.CONFIRMED)
        .values(status=QuoteStatus.PAYMENT_LOCKED, updated_at=_now())
    )
    if (locked.rowcount or 0) != 1:
        db.rollback()
        fresh = db.get(QuoteVersion, quote.id)
        if fresh is not None and fresh.status == QuoteStatus.PAID:
            raise conflict("already_paid", "This quote has already been paid.")
        active = db.scalar(
            select(PaymentAttempt).where(
                PaymentAttempt.quote_version_id == quote.id,
                PaymentAttempt.status.in_(ACTIVE_STATUSES),
            )
        )
        if active is not None:
            return active
        raise conflict(
            "quote_not_payable",
            "Only a confirmed quote can be paid.",
            {"status": fresh.status if fresh is not None else "UNKNOWN"},
        )

    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        active = db.scalar(
            select(PaymentAttempt).where(
                PaymentAttempt.quote_version_id == quote.id,
                PaymentAttempt.status.in_(ACTIVE_STATUSES),
            )
        )
        if active is not None:
            return active
        raise conflict(
            "payment_conflict",
            "Another payment attempt was created for this quote.",
        ) from None
    db.refresh(attempt)
    db.refresh(quote)

    return _create_with_paypal(db, attempt, quote)


def retry_create(db: Session, payment_id: UUID, seller_id: UUID) -> PaymentAttempt:
    """Ask PayPal to create the order again with the same request id.

    Used when the first create call never returned an order id. PayPal dedupes
    on `PayPal-Request-Id`, so a retry either returns the original order or
    creates the one that never happened. Bounded: after `MAX_CREATE_RETRIES`
    the seller has to check PayPal and close the attempt explicitly.
    """
    recover_stale_attempts(db)
    attempt = _load_for_seller(db, payment_id, seller_id)
    if attempt.paypal_order_id:
        raise conflict(
            "order_already_exists",
            "PayPal already returned an order id for this attempt; reconcile instead of retrying.",
        )
    if attempt.status not in {"RECONCILING", "CREATING"}:
        raise conflict(
            "not_recoverable",
            "Only an attempt with an unknown create result can be retried.",
            {"status": attempt.status},
        )
    if attempt.retry_count >= MAX_CREATE_RETRIES:
        raise conflict(
            "retry_limit",
            f"This attempt was already retried {MAX_CREATE_RETRIES} times. "
            "Check PayPal, then close it with a note.",
        )
    _require_paypal_configured()
    quote = db.get(QuoteVersion, attempt.quote_version_id)
    if quote is None:
        raise not_found("Quote not found")

    updated = db.execute(
        update(PaymentAttempt)
        .where(
            PaymentAttempt.id == attempt.id,
            PaymentAttempt.status.in_(("RECONCILING", "CREATING")),
            PaymentAttempt.paypal_order_id.is_(None),
            PaymentAttempt.retry_count < MAX_CREATE_RETRIES,
        )
        .values(
            retry_count=PaymentAttempt.retry_count + 1,
            status="CREATING",
            error_code=None,
            error_detail=None,
            updated_at=_now(),
        )
    )
    if (updated.rowcount or 0) != 1:
        db.rollback()
        fresh = db.get(PaymentAttempt, attempt.id)
        if fresh is None:
            raise not_found("Payment not found")
        if fresh.paypal_order_id:
            raise conflict(
                "order_already_exists",
                "PayPal already returned an order id for this attempt; "
                "reconcile instead of retrying.",
            )
        if fresh.retry_count >= MAX_CREATE_RETRIES:
            raise conflict(
                "retry_limit",
                f"This attempt was already retried {MAX_CREATE_RETRIES} times. "
                "Check PayPal, then close it with a note.",
            )
        raise conflict(
            "not_recoverable",
            "Only an attempt with an unknown create result can be retried.",
            {"status": fresh.status},
        )
    db.commit()
    db.refresh(attempt)
    return _create_with_paypal(db, attempt, quote)


def close_attempt(
    db: Session,
    payment_id: UUID,
    seller_id: UUID,
    note: str,
    confirmed_no_order: bool,
) -> PaymentAttempt:
    """Close an attempt that can never be verified, after a human check.

    This is the only path that unlocks a quote without a PayPal-verified
    outcome, so it demands an explicit acknowledgement and a written note.
    """
    recover_stale_attempts(db)
    attempt = _load_for_seller(db, payment_id, seller_id)
    if attempt.status not in {"RECONCILING", "FAILED"}:
        raise conflict(
            "not_closable",
            "Only an unresolved or failed attempt can be closed.",
            {"status": attempt.status},
        )
    if attempt.paypal_capture_id:
        raise conflict(
            "capture_exists",
            "A capture is recorded for this attempt; it cannot be closed as unpaid.",
        )
    if not confirmed_no_order:
        raise unprocessable(
            "confirmation_required",
            "Confirm that you checked the PayPal dashboard before closing this attempt.",
        )
    cleaned = note.strip()
    if len(cleaned) < 10:
        raise unprocessable(
            "note_required",
            "Write what you checked in PayPal (at least 10 characters).",
        )

    quote = db.get(QuoteVersion, attempt.quote_version_id)
    if quote is not None and quote.status == QuoteStatus.PAID:
        raise conflict("already_paid", "This quote is already paid.")

    resolved_at = _now()
    updated = db.execute(
        update(PaymentAttempt)
        .where(
            PaymentAttempt.id == attempt.id,
            PaymentAttempt.status.in_(("RECONCILING", "FAILED")),
            PaymentAttempt.paypal_capture_id.is_(None),
        )
        .values(
            status="ABANDONED",
            resolved_by=seller_id,
            resolved_at=resolved_at,
            resolution_note=cleaned[:500],
            error_code=attempt.error_code or "closed_without_order",
            updated_at=resolved_at,
        )
    )
    if (updated.rowcount or 0) != 1:
        db.rollback()
        fresh = db.get(PaymentAttempt, attempt.id)
        if fresh is None:
            raise not_found("Payment not found")
        if fresh.status == "COMPLETED" or fresh.paypal_capture_id:
            raise conflict(
                "capture_exists",
                "A capture is recorded for this attempt; it cannot be closed as unpaid.",
            )
        raise conflict(
            "not_closable",
            "Only an unresolved or failed attempt can be closed.",
            {"status": fresh.status},
        )
    db.commit()
    db.refresh(attempt)
    if quote is not None:
        _unlock(db, quote)
    return attempt


def _create_with_paypal(
    db: Session, attempt: PaymentAttempt, quote: QuoteVersion
) -> PaymentAttempt:
    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    try:
        order = paypal.create_order(
            amount_minor=quote.total_minor,
            currency=quote.currency,
            reference_id=f"quote-{quote.quote_number}",
            description=f"ScopeBridge quote v{quote.quote_number}",
            return_url=f"{base}/pay/{attempt.id}",
            cancel_url=f"{base}/pay/{attempt.id}?paypal=cancel",
            request_id=_request_id(attempt, "create"),
        )
    except paypal.PayPalTransportError:
        return _mark(db, attempt, "RECONCILING", "create_unknown", "No usable create response.")
    except paypal.PayPalResponseError as exc:
        if exc.status_code >= 500:
            _mark(db, attempt, "RECONCILING", f"create_{exc.status_code}", exc.issue[:300])
            raise ApiError(
                502,
                "paypal_unavailable",
                "PayPal did not return a usable answer. The attempt will be verified before it "
                "is judged.",
                {"status": exc.status_code},
            ) from exc
        _mark(db, attempt, "FAILED", f"create_{exc.status_code}", exc.issue[:300])
        _unlock(db, quote)
        raise ApiError(
            502,
            "paypal_rejected_order",
            "PayPal did not accept the order. Nothing was charged.",
            {"status": exc.status_code, "issue": exc.issue},
        ) from exc
    except paypal.PayPalError as exc:
        _mark(db, attempt, "FAILED", "paypal_unavailable", None)
        _unlock(db, quote)
        raise ApiError(
            503,
            "paypal_unavailable",
            "PayPal could not be reached or configured. Nothing was charged.",
        ) from exc

    attempt.paypal_order_id = order.id
    attempt.approve_url = order.approve_url
    if not order.id or not order.approve_url:
        return _mark(db, attempt, "RECONCILING", "create_incomplete", "")
    try:
        return _mark(db, attempt, "AWAITING_APPROVAL", None, None)
    except IntegrityError:
        # PayPal handed back an order id that is already recorded elsewhere.
        # Never overwrite the earlier attempt: park this one for verification.
        db.rollback()
        fresh = db.get(PaymentAttempt, attempt.id) or attempt
        return _mark(db, fresh, "RECONCILING", "order_id_conflict", order.id[:40])


def capture_payment(
    db: Session, requirement: Requirement, payment_id: UUID
) -> PaymentAttempt:
    recover_stale_attempts(db)
    attempt = _load(db, requirement, payment_id)
    if attempt.status == "COMPLETED":
        return attempt
    if attempt.status not in {"AWAITING_APPROVAL", "RECONCILING", "CAPTURING"}:
        raise conflict("payment_not_capturable", "This payment cannot be captured.", {
            "status": attempt.status,
        })
    if not attempt.paypal_order_id:
        raise conflict("payment_not_capturable", "PayPal never returned an order id.")

    updated = db.execute(
        update(PaymentAttempt)
        .where(
            PaymentAttempt.id == attempt.id,
            PaymentAttempt.status.in_(("AWAITING_APPROVAL", "RECONCILING", "CAPTURING")),
        )
        .values(status="CAPTURING", updated_at=_now())
    )
    if (updated.rowcount or 0) != 1:
        db.rollback()
        fresh = db.get(PaymentAttempt, attempt.id)
        if fresh is not None and fresh.status == "COMPLETED":
            return fresh
        raise conflict(
            "payment_not_capturable",
            "This payment cannot be captured.",
            {"status": fresh.status if fresh is not None else "UNKNOWN"},
        )
    db.commit()
    db.refresh(attempt)

    try:
        payload = paypal.capture_order(
            attempt.paypal_order_id, request_id=_request_id(attempt, "capture")
        )
    except paypal.PayPalTransportError:
        return _mark(db, attempt, "RECONCILING", "capture_unknown", "No usable capture response.")
    except paypal.PayPalResponseError as exc:
        return _handle_capture_error(db, attempt, exc)
    except paypal.PayPalError as exc:
        _mark(db, attempt, "FAILED", "paypal_unavailable", None)
        quote = db.get(QuoteVersion, attempt.quote_version_id)
        if quote is not None:
            _unlock(db, quote)
        raise ApiError(
            503,
            "paypal_unavailable",
            "PayPal could not be reached or configured. Nothing was charged.",
        ) from exc

    return _finalize(db, attempt, payload)


def reconcile_payment(db: Session, payment_id: UUID, seller_id: UUID) -> PaymentAttempt:
    return reconcile(db, _load_for_seller(db, payment_id, seller_id))


def reconcile(db: Session, attempt: PaymentAttempt) -> PaymentAttempt:
    if attempt.status == "COMPLETED":
        return attempt
    if not attempt.paypal_order_id:
        raise conflict(
            "no_order_id",
            "This attempt never received a PayPal order id, so there is nothing to query. "
            "Retry the create call, or close the attempt after checking PayPal.",
            {"retry_count": attempt.retry_count},
        )
    quote = db.get(QuoteVersion, attempt.quote_version_id)
    if quote is None:
        raise not_found("Quote not found")

    try:
        order = paypal.get_order(attempt.paypal_order_id)
    except paypal.PayPalTransportError:
        return _mark(db, attempt, "RECONCILING", "reconcile_unknown", "No usable query response.")
    except paypal.PayPalResponseError as exc:
        if exc.status_code == 404:
            return _fail_and_unlock(
                db, attempt, quote, "order_missing", "PayPal has no such order."
            )
        return _mark(db, attempt, "RECONCILING", f"reconcile_{exc.status_code}", exc.issue[:300])
    except paypal.PayPalError as exc:
        _mark(db, attempt, "RECONCILING", "reconcile_unavailable", None)
        raise ApiError(
            503,
            "paypal_unavailable",
            "PayPal could not be reached or configured. The attempt stays in verification.",
        ) from exc

    status = order.get("status", "")
    if status == "COMPLETED":
        return _finalize(db, attempt, order)
    if status == "APPROVED":
        try:
            payload = paypal.capture_order(
                attempt.paypal_order_id, request_id=_request_id(attempt, "capture")
            )
        except paypal.PayPalTransportError as exc:
            return _mark(db, attempt, "RECONCILING", "capture_unknown", str(exc)[:300])
        except paypal.PayPalResponseError as exc:
            return _handle_capture_error(db, attempt, exc)
        return _finalize(db, attempt, payload)
    if status in {"VOIDED", "EXPIRED"}:
        return _fail_and_unlock(
            db, attempt, quote, f"order_{status.lower()}", f"PayPal reports {status}."
        )
    return _mark(db, attempt, "AWAITING_APPROVAL", None, None)


def list_attention(db: Session, seller_id: UUID) -> list[AttentionPaymentOut]:
    """Every attempt the seller may need to resolve, newest activity first.

    CREATING, AWAITING_APPROVAL, CAPTURING and RECONCILING are all non-terminal;
    an attempt on an already-paid quote is still shown because it may represent
    a conflicting second capture.
    """
    recover_stale_attempts(db)
    rows = db.execute(
        select(PaymentAttempt, Requirement, QuoteVersion)
        .join(Requirement, Requirement.id == PaymentAttempt.requirement_id)
        .join(QuoteVersion, QuoteVersion.id == PaymentAttempt.quote_version_id)
        .where(
            Requirement.seller_id == seller_id,
            or_(
                PaymentAttempt.status.in_(ACTIVE_STATUSES),
                and_(
                    PaymentAttempt.status == "FAILED",
                    QuoteVersion.status != QuoteStatus.PAID,
                ),
            ),
        )
        .order_by(PaymentAttempt.updated_at.desc())
    ).all()
    return [
        serialize_attention(attempt, requirement, quote)
        for attempt, requirement, quote in rows
    ]


def list_for_requirement(db: Session, requirement_id: UUID) -> list[PaymentOut]:
    recover_stale_attempts(db)
    rows = db.scalars(
        select(PaymentAttempt)
        .where(PaymentAttempt.requirement_id == requirement_id)
        .order_by(PaymentAttempt.created_at.desc())
    ).all()
    return [serialize_attempt(row) for row in rows]


def snapshot_for_requirement(db: Session, requirement_id: UUID) -> OrderSnapshot | None:
    return db.scalar(
        select(OrderSnapshot).where(OrderSnapshot.requirement_id == requirement_id)
    )


def load_snapshot_for_seller(db: Session, snapshot_id: UUID, seller_id: UUID) -> OrderSnapshot:
    snapshot = db.get(OrderSnapshot, snapshot_id)
    if snapshot is None:
        raise not_found("Order not found")
    requirement = db.get(Requirement, snapshot.requirement_id)
    if requirement is None or requirement.seller_id != seller_id:
        raise not_found("Order not found")
    return snapshot


def serialize_attempt(attempt: PaymentAttempt) -> PaymentOut:
    return PaymentOut(
        id=attempt.id,
        quote_id=attempt.quote_version_id,
        requirement_id=attempt.requirement_id,
        status=attempt.status,
        amount_minor=attempt.amount_minor,
        currency=attempt.currency,
        approve_url=attempt.approve_url,
        paypal_order_id=attempt.paypal_order_id,
        paypal_capture_id=attempt.paypal_capture_id,
        error_code=attempt.error_code,
        retry_count=attempt.retry_count,
        resolved_at=attempt.resolved_at,
        resolution_note=attempt.resolution_note,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
    )


def serialize_attention(
    attempt: PaymentAttempt, requirement: Requirement, quote: QuoteVersion
) -> AttentionPaymentOut:
    return AttentionPaymentOut(
        **serialize_attempt(attempt).model_dump(),
        client_name=requirement.client_name,
        client_business=requirement.client_business,
        quote_number=quote.quote_number,
    )


def serialize_snapshot(snapshot: OrderSnapshot) -> SnapshotOut:
    return SnapshotOut(
        id=snapshot.id,
        requirement_id=snapshot.requirement_id,
        quote_id=snapshot.quote_version_id,
        order_id=snapshot.paypal_order_id,
        capture_id=snapshot.paypal_capture_id,
        amount_minor=snapshot.amount_minor,
        currency=snapshot.currency,
        payer_email=snapshot.payer_email,
        captured_at=snapshot.captured_at,
        items=[SnapshotItemOut(**item) for item in snapshot.items],
    )


def _load_for_seller(db: Session, payment_id: UUID, seller_id: UUID) -> PaymentAttempt:
    recover_stale_attempts(db)
    attempt = db.get(PaymentAttempt, payment_id)
    if attempt is None:
        raise not_found("Payment not found")
    requirement = db.get(Requirement, attempt.requirement_id)
    if requirement is None or requirement.seller_id != seller_id:
        raise not_found("Payment not found")
    return attempt


def load_for_client(db: Session, payment_id: UUID, client_id: UUID) -> PaymentAttempt:
    recover_stale_attempts(db)
    attempt = db.get(PaymentAttempt, payment_id)
    if attempt is None:
        raise not_found("Payment not found")
    requirement = db.get(Requirement, attempt.requirement_id)
    if requirement is None or requirement.client_id != client_id:
        raise not_found("Payment not found")
    return attempt


def _load(db: Session, requirement: Requirement, payment_id: UUID) -> PaymentAttempt:
    attempt = db.get(PaymentAttempt, payment_id)
    if attempt is None or attempt.requirement_id != requirement.id:
        raise not_found("Payment not found")
    return attempt


def _handle_capture_error(
    db: Session, attempt: PaymentAttempt, exc: paypal.PayPalResponseError
) -> PaymentAttempt:
    quote = db.get(QuoteVersion, attempt.quote_version_id)
    issue = exc.issue
    if issue == "ORDER_ALREADY_CAPTURED":
        # This attempt may be the second of two concurrent captures. The only
        # safe move is to read the original order and let the verified capture
        # decide the local state; never downgrade a COMPLETED attempt blind.
        if not attempt.paypal_order_id:
            return _mark(
                db,
                attempt,
                "RECONCILING",
                "already_captured_no_order",
                "PayPal reports a capture but no order id is recorded.",
            )
        try:
            order = paypal.get_order(attempt.paypal_order_id)
        except paypal.PayPalError:
            return _mark(
                db,
                attempt,
                "RECONCILING",
                "already_captured_verify",
                "PayPal reported an existing capture; the order still needs a query.",
            )
        if order.get("status") == "COMPLETED":
            return _finalize(db, attempt, order)
        return _mark(
            db,
            attempt,
            "RECONCILING",
            "already_captured_verify",
            "PayPal reported an existing capture but the order is not COMPLETED.",
        )
    if issue == "ORDER_NOT_APPROVED":
        return _mark(
            db,
            attempt,
            "AWAITING_APPROVAL",
            "not_approved",
            "The buyer has not approved this order yet.",
        )
    if exc.status_code >= 500:
        return _mark(db, attempt, "RECONCILING", f"capture_{exc.status_code}", issue[:300])
    if quote is None:
        return _mark(db, attempt, "FAILED", "capture_failed", issue[:300])
    return _fail_and_unlock(
        db, attempt, quote, f"capture_{issue or exc.status_code}", "PayPal declined the capture."
    )


def _finalize(db: Session, attempt: PaymentAttempt, payload: dict[str, Any]) -> PaymentAttempt:
    quote = db.get(QuoteVersion, attempt.quote_version_id)
    if quote is None:
        raise not_found("Quote not found")

    capture = paypal.capture_of(payload)
    if capture is None:
        return _mark(db, attempt, "RECONCILING", "capture_missing", "No capture object returned.")
    capture_id = str(capture.get("id") or "")
    if not capture_id:
        return _mark(db, attempt, "RECONCILING", "capture_missing_id", "No capture id returned.")
    if not attempt.paypal_order_id:
        return _mark(
            db,
            attempt,
            "RECONCILING",
            "capture_missing_order",
            "A capture was reported without a recorded order id.",
        )

    if capture.get("status") != "COMPLETED":
        return _mark(
            db,
            attempt,
            "RECONCILING",
            f"capture_{str(capture.get('status', 'unknown')).lower()}",
            "Capture is not completed.",
        )
    if not paypal.amount_matches(capture, attempt.amount_minor, attempt.currency):
        return _mark(
            db,
            attempt,
            "RECONCILING",
            "capture_amount_mismatch",
            "Amount or currency differs.",
        )

    merchant = get_settings().paypal_merchant_id
    payee = capture.get("payee") or {}
    if merchant and payee.get("merchant_id") not in (None, "", merchant):
        return _mark(db, attempt, "RECONCILING", "capture_merchant_mismatch", "Unexpected payee.")

    existing = db.scalar(
        select(OrderSnapshot).where(OrderSnapshot.quote_version_id == quote.id)
    )
    if existing is not None:
        if existing.paypal_capture_id != capture_id:
            return _mark(
                db,
                attempt,
                "RECONCILING",
                "capture_conflict",
                "A different capture is already recorded for this quote.",
            )
        return _repair_paid(db, attempt, quote)

    captured_at = _now()
    snapshot = OrderSnapshot(
        requirement_id=attempt.requirement_id,
        quote_version_id=quote.id,
        paypal_order_id=attempt.paypal_order_id,
        paypal_capture_id=capture_id,
        amount_minor=attempt.amount_minor,
        currency=attempt.currency,
        payer_email=(payload.get("payer") or {}).get("email_address", ""),
        merchant_id=payee.get("merchant_id", ""),
        items=[
            {
                "code": item.code,
                "label": item.label,
                "amount_minor": item.amount_minor,
                "included": item.included,
            }
            for item in quote.items
        ],
        captured_at=captured_at,
    )
    try:
        db.add(snapshot)
        # Finalization only writes COMPLETED, so it may repair a stale
        # RECONCILING/FAILED/ABANDONED attempt. It never downgrades a completed one.
        marked = db.execute(
            update(PaymentAttempt)
            .where(
                PaymentAttempt.id == attempt.id,
                or_(
                    PaymentAttempt.paypal_capture_id.is_(None),
                    PaymentAttempt.paypal_capture_id == capture_id,
                ),
            )
            .values(
                status="COMPLETED",
                paypal_capture_id=capture_id,
                error_code=None,
                error_detail=None,
                updated_at=captured_at,
            )
        )
        if (marked.rowcount or 0) != 1:
            db.rollback()
            fresh = db.get(PaymentAttempt, attempt.id)
            if fresh is not None and fresh.status == "COMPLETED":
                return fresh
            return _mark(
                db,
                fresh or attempt,
                "RECONCILING",
                "capture_conflict",
                "A different capture is already recorded for this attempt.",
            )
        # A verified capture is the repair path for a quote that was unlocked
        # after an earlier failure. The state machine is not allowed to reject
        # money that PayPal has already taken.
        db.execute(
            update(QuoteVersion)
            .where(QuoteVersion.id == quote.id, QuoteVersion.status != QuoteStatus.PAID)
            .values(status=QuoteStatus.PAID, updated_at=captured_at)
        )
        db.execute(
            update(Requirement)
            .where(
                Requirement.id == attempt.requirement_id,
                Requirement.status != CLOSED_STATUS,
            )
            .values(status=CLOSED_STATUS, updated_at=captured_at)
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(OrderSnapshot).where(OrderSnapshot.quote_version_id == quote.id)
        )
        fresh = db.get(PaymentAttempt, attempt.id)
        if existing is not None and existing.paypal_capture_id == capture_id:
            return _repair_paid(db, fresh or attempt, quote)
        if fresh is not None and fresh.status == "COMPLETED":
            return fresh
        return _mark(
            db,
            fresh or attempt,
            "RECONCILING",
            "capture_conflict",
            "A different capture is already recorded for this quote.",
        )
    db.refresh(attempt)
    return attempt


def _repair_paid(
    db: Session, attempt: PaymentAttempt, quote: QuoteVersion
) -> PaymentAttempt:
    """Bring an already-snapshotted quote back to PAID without inserting twice."""
    now = _now()
    db.execute(
        update(PaymentAttempt)
        .where(PaymentAttempt.id == attempt.id)
        .values(
            status="COMPLETED",
            error_code=None,
            error_detail=None,
            updated_at=now,
        )
    )
    db.execute(
        update(QuoteVersion)
        .where(QuoteVersion.id == quote.id, QuoteVersion.status != QuoteStatus.PAID)
        .values(status=QuoteStatus.PAID, updated_at=now)
    )
    db.execute(
        update(Requirement)
        .where(Requirement.id == attempt.requirement_id, Requirement.status != CLOSED_STATUS)
        .values(status=CLOSED_STATUS, updated_at=now)
    )
    db.commit()
    db.refresh(attempt)
    return attempt


def _fail_and_unlock(
    db: Session, attempt: PaymentAttempt, quote: QuoteVersion, code: str, detail: str
) -> PaymentAttempt:
    _mark(db, attempt, "FAILED", code, detail)
    _unlock(db, quote)
    return attempt


def _unlock(db: Session, quote: QuoteVersion) -> None:
    db.execute(
        update(QuoteVersion)
        .where(QuoteVersion.id == quote.id, QuoteVersion.status == QuoteStatus.PAYMENT_LOCKED)
        .values(status=QuoteStatus.CONFIRMED, updated_at=_now())
    )
    db.commit()
    db.refresh(quote)


def _mark(
    db: Session,
    attempt: PaymentAttempt,
    status: str,
    code: str | None,
    detail: str | None,
) -> PaymentAttempt:
    # A late error branch must never overwrite a verified COMPLETED attempt.
    db.execute(
        update(PaymentAttempt)
        .where(PaymentAttempt.id == attempt.id, PaymentAttempt.status != "COMPLETED")
        .values(
            status=status,
            error_code=code,
            error_detail=detail,
            updated_at=_now(),
        )
    )
    db.commit()
    db.refresh(attempt)
    return attempt


def _request_id(attempt: PaymentAttempt, phase: str) -> str:
    return f"sb-{attempt.id.hex[:24]}-{phase}"
