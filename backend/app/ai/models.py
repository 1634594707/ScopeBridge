"""Evidence table for every model call."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AiExtraction(Base):
    __tablename__ = "ai_extractions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    source_revision: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(40))
    input_message_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_output: Mapped[str] = mapped_column(Text, default="")
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="OK", index=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
