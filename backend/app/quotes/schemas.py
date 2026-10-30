"""Wire schemas for quote versions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteItemOut(BaseModel):
    id: UUID
    position: int
    code: str
    label: str
    amount_minor: int
    rule_ref: str
    source_message_id: UUID | None
    included: bool


class QuoteOut(BaseModel):
    id: UUID
    requirement_id: UUID
    proposal_id: UUID
    quote_number: int
    source_revision: int
    currency: str
    total_minor: int
    status: str
    scope_summary: str
    reviewed_at: datetime | None
    confirmed_at: datetime | None
    superseded_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    items: list[QuoteItemOut]


class QuoteCreate(BaseModel):
    proposal_id: UUID
    scope_summary: str = Field(default="", max_length=2000)
