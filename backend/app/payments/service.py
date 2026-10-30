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

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, conflict, not_found
from app.payments.models import ACTIVE_STATUSES, OrderSnapshot, PaymentAttempt
from app.payments.schemas import PaymentOut, SnapshotItemOut, SnapshotOut
from app.paypal import client as paypal
from app.quotes.models import QuoteVersion
from app.quotes.states import QuoteAction, QuoteStatus, transition
from app.requirements.models import Requirement


def start_payment(
    db: Session, requirement: Requirement, quote_id: UUID, idempotency_key: str
) -> PaymentAttempt:
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

    if quote.status == QuoteStatus.PAID:
        raise conflict("already_paid", "This quote has already been paid.")
    if quote.status != QuoteStatus.CONFIRMED:
        raise conflict(
            "quote_not_payable",
            "Only a confirmed quote can be paid.",
            {"status": quote.status},
        )

    attempt = PaymentAttempt(
        quote_version_id=quote.id,
        requirement_id=requirement.id,
        status="CREATING",
        idempotency_key=idempotency_key,
        amount_minor=quote.total_minor,
        currency=quote.currency,
    )
    quote.status = transition(quote.status, QuoteAction.LOCK_FOR_PAYMENT)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

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
    except paypal.PayPalTransportError as exc:
        return _mark(db, attempt, "RECONCILING", "create_unknown", str(exc)[:300])
    except paypal.PayPalResponseError as exc:
        _mark(db, attempt, "FAILED", f"create_{exc.status_code}", exc.issue[:300])
        _unlock(db, quote)
        raise ApiError(
            502,
            "paypal_rejected_order",
            "PayPal did not accept the order. Nothing was charged.",
            {"status": exc.status_code, "issue": exc.issue},
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
    attempt = _load(db, requirement, payment_id)
    if attempt.status == "COMPLETED":
        return attempt
    if attempt.status not in {"AWAITING_APPROVAL", "RECONCILING", "CAPTURING"}:
        raise conflict("payment_not_capturable", "This payment cannot be captured.", {
            "status": attempt.status,
        })
    if not attempt.paypal_order_id:
        raise conflict("payment_not_capturable", "PayPal never returned an order id.")

    attempt.status = "CAPTURING"
    db.commit()

    try:
        payload = paypal.capture_order(
            attempt.paypal_order_id, request_id=_request_id(attempt, "capture")
        )
    except paypal.PayPalTransportError as exc:
        return _mark(db, attempt, "RECONCILING", "capture_unknown", str(exc)[:300])
    except paypal.PayPalResponseError as exc:
        return _handle_capture_error(db, attempt, exc)

    return _finalize(db, attempt, payload)


def reconcile_payment(db: Session, payment_id: UUID, seller_id: UUID) -> PaymentAttempt:
    attempt = db.get(PaymentAttempt, payment_id)
    if attempt is None:
        raise not_found("Payment not found")
    requirement = db.get(Requirement, attempt.requirement_id)
    if requirement is None or requirement.seller_id != seller_id:
        raise not_found("Payment not found")
    return reconcile(db, attempt)


def reconcile(db: Session, attempt: PaymentAttempt) -> PaymentAttempt:
    if attempt.status == "COMPLETED" or not attempt.paypal_order_id:
        return attempt
    quote = db.get(QuoteVersion, attempt.quote_version_id)
    if quote is None:
        raise not_found("Quote not found")

    try:
        order = paypal.get_order(attempt.paypal_order_id)
    except paypal.PayPalTransportError as exc:
        return _mark(db, attempt, "RECONCILING", "reconcile_unknown", str(exc)[:300])
    except paypal.PayPalResponseError as exc:
        if exc.status_code == 404:
            return _fail_and_unlock(
                db, attempt, quote, "order_missing", "PayPal has no such order."
            )
        return _mark(db, attempt, "RECONCILING", f"reconcile_{exc.status_code}", exc.issue[:300])

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


def list_for_requirement(db: Session, requirement_id: UUID) -> list[PaymentOut]:
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
        status=attempt.status,
        amount_minor=attempt.amount_minor,
        currency=attempt.currency,
        approve_url=attempt.approve_url,
        paypal_order_id=attempt.paypal_order_id,
        paypal_capture_id=attempt.paypal_capture_id,
        error_code=attempt.error_code,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
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


def load_for_requirement(
    db: Session, requirement: Requirement, payment_id: UUID
) -> PaymentAttempt:
    return _load(db, requirement, payment_id)


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
        return _mark(db, attempt, "RECONCILING", "already_captured", "Verifying with PayPal.")
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

    captured_at = datetime.now(UTC)
    snapshot = OrderSnapshot(
        requirement_id=attempt.requirement_id,
        quote_version_id=quote.id,
        paypal_order_id=attempt.paypal_order_id or capture.get("id", ""),
        paypal_capture_id=capture.get("id", ""),
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
    attempt.status = "COMPLETED"
    attempt.paypal_capture_id = capture.get("id", "")
    attempt.error_code = None
    attempt.error_detail = None
    if quote.status != QuoteStatus.PAID:
        quote.status = transition(quote.status, QuoteAction.MARK_PAID)
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.get(PaymentAttempt, attempt.id) or attempt
    db.refresh(attempt)
    return attempt


def _fail_and_unlock(
    db: Session, attempt: PaymentAttempt, quote: QuoteVersion, code: str, detail: str
) -> PaymentAttempt:
    _mark(db, attempt, "FAILED", code, detail)
    _unlock(db, quote)
    return attempt


def _unlock(db: Session, quote: QuoteVersion) -> None:
    if quote.status == QuoteStatus.PAYMENT_LOCKED:
        quote.status = transition(quote.status, QuoteAction.UNLOCK_AFTER_FAILURE)
        db.commit()


def _mark(
    db: Session,
    attempt: PaymentAttempt,
    status: str,
    code: str | None,
    detail: str | None,
) -> PaymentAttempt:
    attempt.status = status
    attempt.error_code = code
    attempt.error_detail = detail
    db.commit()
    db.refresh(attempt)
    return attempt


def _request_id(attempt: PaymentAttempt, phase: str) -> str:
    return f"sb-{attempt.id.hex[:24]}-{phase}"
