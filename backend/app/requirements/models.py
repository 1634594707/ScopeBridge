"""Requirement and message tables.

`requirement.revision` is the concurrency token: appending a message must name
the revision it was written against, and the append increments it.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
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


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    client_name: Mapped[str] = mapped_column(String(120))
    client_business: Mapped[str] = mapped_column(String(160), default="")
    client_email: Mapped[str] = mapped_column(String(255), default="")
    portal_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list[RequirementMessage]] = relationship(
        back_populates="requirement",
        order_by="RequirementMessage.revision",
        cascade="all, delete-orphan",
    )


class RequirementMessage(Base):
    __tablename__ = "requirement_messages"
    __table_args__ = (
        UniqueConstraint("requirement_id", "revision", name="uq_messages_requirement_revision"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    author: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(Text)
    budget_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    assets_ready: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    requirement: Mapped[Requirement] = relationship(back_populates="messages")
