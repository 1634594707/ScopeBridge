"""Proposal table: a candidate scope plus the verdict it received."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    rule_version_id: Mapped[UUID] = mapped_column(ForeignKey("service_rule_versions.id"))
    source_revision: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(120))
    pages: Mapped[int] = mapped_column(Integer)
    addon_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_features: Mapped[list[str]] = mapped_column(JSON, default=list)
    assets_ready: Mapped[bool] = mapped_column(Boolean, default=True)
    feasible: Mapped[bool] = mapped_column(Boolean, default=False)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    violations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    selected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
