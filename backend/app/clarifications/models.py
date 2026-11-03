"""Clarification records for the AI-assisted quote gate.

A clarification belongs to one requirement revision. The latest record for that
revision decides whether a quote may be created; older records remain as audit
history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

KIND_AI = "AI"
KIND_MANUAL = "MANUAL"
STATUS_PENDING = "PENDING"
STATUS_CONFIRMED = "CONFIRMED"


class RequirementClarification(Base):
    __tablename__ = "requirement_clarifications"
    __table_args__ = (
        Index(
            "ix_clarifications_requirement_revision",
            "requirement_id",
            "source_revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    source_revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12), default=STATUS_PENDING, index=True)
    extraction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_extractions.id", ondelete="SET NULL"), nullable=True
    )
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    unsupported_requests: Mapped[list[str]] = mapped_column(JSON, default=list)
    answers: Mapped[str] = mapped_column(Text, default="")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_unsupported: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def clarification_payload(row: RequirementClarification) -> dict[str, Any]:
    return {
        "id": row.id,
        "requirement_id": row.requirement_id,
        "source_revision": row.source_revision,
        "kind": row.kind,
        "status": row.status,
        "questions": row.questions or [],
        "unsupported_requests": row.unsupported_requests or [],
        "answers": row.answers,
        "acknowledged": row.acknowledged,
        "acknowledged_unsupported": row.acknowledged_unsupported,
        "reason_code": row.reason_code,
        "note": row.note,
        "confirmed_at": row.confirmed_at,
        "created_at": row.created_at,
    }
