"""Service rule versions.

A version is immutable: changing a price creates a new row, so every historical
quote keeps pointing at the numbers it was priced with.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ServiceRuleVersion(Base):
    __tablename__ = "service_rule_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_no: Mapped[int] = mapped_column(Integer, unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    base_page_minor: Mapped[int] = mapped_column(Integer)
    extra_page_minor: Mapped[int] = mapped_column(Integer)
    revisions_included: Mapped[int] = mapped_column(Integer)
    lead_time_days: Mapped[int] = mapped_column(Integer)
    asset_buffer_days: Mapped[int] = mapped_column(Integer, default=3)
    addons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    exclusions: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
