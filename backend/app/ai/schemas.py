"""What the model is allowed to return, and what the API returns to the studio.

`extra="forbid"` is deliberate: an unexpected key means the model improvised,
and improvised fields must not reach the pricing layer.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.proposals.schemas import ViolationOut


class ModelFacts(BaseModel):
    """The five facts the model is allowed to state."""

    model_config = ConfigDict(extra="forbid")

    # 0 is allowed so "no pages" reaches the rule layer and is reported as
    # invalid_scope instead of being rejected as a malformed answer.
    pages: int | None = Field(default=None, ge=0, le=20)
    budget_usd: float | None = Field(default=None, ge=0)
    deadline_days: int | None = Field(default=None, ge=0, le=365)
    assets_ready: bool | None = None
    features: list[str] = Field(default_factory=list)


class FactsOut(BaseModel):
    pages: int | None
    budget_usd: float | None
    deadline_days: int | None
    assets_ready: bool | None
    features: list[str]


class RecordOut(BaseModel):
    revision: int
    budget_minor: int | None
    deadline: date | None
    assets_ready: bool | None


class PricedCandidateOut(BaseModel):
    label: str
    pages: int
    addon_codes: list[str]
    requested_features: list[str]
    rationale: str
    feasible: bool
    total_minor: int
    currency: str
    violations: list[ViolationOut]


class ExtractionOut(BaseModel):
    id: UUID
    model: str
    prompt_version: str
    latency_ms: int
    created_at: datetime
    facts: FactsOut
    record: RecordOut
    source_message_ids: list[str]
    unsupported_requests: list[str]
    questions: list[str]
    candidates: list[PricedCandidateOut]


class ExtractionEnvelope(BaseModel):
    """Wraps the optional last draft so "nothing yet" is a 200, not a 404."""

    extraction: ExtractionOut | None
