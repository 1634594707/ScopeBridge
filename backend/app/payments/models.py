"""Payment attempt and paid order snapshot.

At most one attempt per quote may be active at a time; that is enforced by a
partial unique index, not by application code alone. A snapshot is written in
the same transaction as the PAID transition and is never updated afterwards.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ACTIVE_STATUSES = ("CREATING", "AWAITING_APPROVAL", "CAPTURING", "RECONCILING")


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        Index(
            "uq_payment_attempts_active_quote",
            "quote_version_id",
            unique=True,
            postgresql_where=text(
                "status IN ('CREATING', 'AWAITING_APPROVAL', 'CAPTURING', 'RECONCILING')"
            ),
        ),
        Index("ix_payment_attempts_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    quote_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("quote_versions.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="CREATING")
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    paypal_order_id: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )
    paypal_capture_id: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )
    approve_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrderSnapshot(Base):
    __tablename__ = "order_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="RESTRICT"), index=True
    )
    quote_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("quote_versions.id", ondelete="RESTRICT"), unique=True
    )
    paypal_order_id: Mapped[str] = mapped_column(String(40), unique=True)
    paypal_capture_id: Mapped[str] = mapped_column(String(40), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    payer_email: Mapped[str] = mapped_column(String(255), default="")
    merchant_id: Mapped[str] = mapped_column(String(64), default="")
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
