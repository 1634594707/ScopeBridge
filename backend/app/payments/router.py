"""Payment endpoints for the client portal and the seller console."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import SellerAuth, require_csrf, require_customer, require_seller
from app.core.db import get_db
from app.payments import service
from app.payments.schemas import (
    ClosePaymentRequest,
    PaymentOut,
    SnapshotEnvelope,
    SnapshotOut,
)
from app.requirements.models import Requirement
from app.requirements.service import load_for_seller

router = APIRouter(tags=["payments"])


@router.post("/portal/quotes/{quote_id}/payment-attempts", response_model=PaymentOut)
def create_payment_attempt(
    quote_id: UUID,
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=8, max_length=80
    ),
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.start_payment(db, requirement, quote_id, idempotency_key)
    return service.serialize_attempt(attempt)


@router.get("/portal/payments/{payment_id}", response_model=PaymentOut)
def read_payment(
    payment_id: UUID,
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.load_for_requirement(db, requirement, payment_id)
    return service.serialize_attempt(attempt)


@router.post("/portal/payments/{payment_id}/capture", response_model=PaymentOut)
def capture_payment(
    payment_id: UUID,
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.capture_payment(db, requirement, payment_id)
    return service.serialize_attempt(attempt)


@router.post("/payments/{payment_id}/reconcile", response_model=PaymentOut)
def reconcile_payment(
    payment_id: UUID,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.reconcile_payment(db, payment_id, auth.user.id)
    return service.serialize_attempt(attempt)


@router.post("/payments/{payment_id}/retry-create", response_model=PaymentOut)
def retry_create_order(
    payment_id: UUID,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.retry_create(db, payment_id, auth.user.id)
    return service.serialize_attempt(attempt)


@router.post("/payments/{payment_id}/close", response_model=PaymentOut)
def close_payment(
    payment_id: UUID,
    payload: ClosePaymentRequest,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PaymentOut:
    attempt = service.close_attempt(
        db,
        payment_id,
        auth.user.id,
        note=payload.note,
        confirmed_no_order=payload.confirmed_no_order,
    )
    return service.serialize_attempt(attempt)


@router.get("/requirements/{requirement_id}/payments", response_model=list[PaymentOut])
def list_payments(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> list[PaymentOut]:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    return service.list_for_requirement(db, requirement.id)


@router.get("/requirements/{requirement_id}/order", response_model=SnapshotEnvelope)
def read_requirement_order(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> SnapshotEnvelope:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    snapshot = service.snapshot_for_requirement(db, requirement.id)
    return SnapshotEnvelope(
        order=service.serialize_snapshot(snapshot) if snapshot else None
    )


@router.get("/orders/{snapshot_id}", response_model=SnapshotOut)
def read_order(
    snapshot_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> SnapshotOut:
    snapshot = service.load_snapshot_for_seller(db, snapshot_id, auth.user.id)
    return service.serialize_snapshot(snapshot)
