"""Quote version and quote item tables.

A version is frozen the moment it is created; later changes create a new
version with a higher `quote_number` and mark the previous one `SUPERSEDED`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class QuoteVersion(Base):
    __tablename__ = "quote_versions"
    __table_args__ = (
        UniqueConstraint("requirement_id", "quote_number", name="uq_quotes_requirement_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    proposal_id: Mapped[UUID] = mapped_column(ForeignKey("proposals.id", ondelete="RESTRICT"))
    rule_version_id: Mapped[UUID] = mapped_column(ForeignKey("service_rule_versions.id"))
    quote_number: Mapped[int] = mapped_column(Integer)
    source_revision: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    total_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    scope_summary: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[QuoteItem]] = relationship(
        back_populates="quote",
        order_by="QuoteItem.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    quote_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("quote_versions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(160))
    amount_minor: Mapped[int] = mapped_column(Integer)
    rule_ref: Mapped[str] = mapped_column(String(80))
    source_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("requirement_messages.id", ondelete="SET NULL"), nullable=True
    )
    included: Mapped[bool] = mapped_column(Boolean, default=True)

    quote: Mapped[QuoteVersion] = relationship(back_populates="items")
