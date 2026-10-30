"""Wire schemas for candidate scopes."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ViolationOut(BaseModel):
    code: str
    detail: str
    rule_ref: str


class ProposalCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    pages: int = Field(ge=1, le=20)
    addon_codes: list[str] = Field(default_factory=list)
    requested_features: list[str] = Field(default_factory=list)
    assets_ready: bool = True
    budget_minor: int | None = Field(default=None, ge=0, le=10_000_000)
    deadline: date | None = None


class ProposalOut(BaseModel):
    id: UUID
    requirement_id: UUID
    source_revision: int
    label: str
    pages: int
    addon_codes: list[str]
    requested_features: list[str]
    assets_ready: bool
    feasible: bool
    total_minor: int
    currency: str
    violations: list[ViolationOut]
    selected_at: datetime | None
    created_at: datetime
