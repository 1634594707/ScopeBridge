"""Wire schemas for payment attempts and order snapshots."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: UUID
    quote_id: UUID
    status: str
    amount_minor: int
    currency: str
    approve_url: str | None
    paypal_order_id: str | None
    paypal_capture_id: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class SnapshotItemOut(BaseModel):
    code: str
    label: str
    amount_minor: int
    included: bool


class SnapshotOut(BaseModel):
    id: UUID
    requirement_id: UUID
    quote_id: UUID
    order_id: str
    capture_id: str
    amount_minor: int
    currency: str
    payer_email: str
    captured_at: datetime
    items: list[SnapshotItemOut]


class SnapshotEnvelope(BaseModel):
    order: SnapshotOut | None

