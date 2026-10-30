"""Wire schemas for requirements, messages and the client portal."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.payments.schemas import PaymentOut, SnapshotOut
from app.proposals.schemas import ProposalOut
from app.quotes.schemas import QuoteOut


class MessageOut(BaseModel):
    id: UUID
    author: str
    body: str
    budget_minor: int | None
    deadline: date | None
    assets_ready: bool | None
    revision: int
    created_at: datetime


class RequirementSummary(BaseModel):
    id: UUID
    client_name: str
    client_business: str
    revision: int
    status: str
    budget_minor: int | None
    deadline: date | None
    assets_ready: bool | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class RequirementDetail(BaseModel):
    requirement: RequirementSummary
    messages: list[MessageOut]


class IntakeRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=120)
    client_business: str = Field(default="", max_length=160)
    client_email: str = Field(default="", max_length=255)
    message: str = Field(min_length=10, max_length=4000)
    budget_minor: int = Field(ge=0, le=10_000_000)
    deadline: date
    assets_ready: bool


class IntakeResponse(BaseModel):
    requirement_id: UUID
    portal_token: str
    portal_path: str


class AddMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    expected_revision: int = Field(ge=1)
    budget_minor: int | None = Field(default=None, ge=0, le=10_000_000)
    deadline: date | None = None
    assets_ready: bool | None = None


class PortalView(BaseModel):
    requirement: RequirementSummary
    messages: list[MessageOut]
    proposals: list[ProposalOut]
    quotes: list[QuoteOut]
    payments: list[PaymentOut]
    order: SnapshotOut | None
    service_rule_version: int
    currency: str
