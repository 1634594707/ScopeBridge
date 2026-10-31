"""Wire schemas for the published rule set and the public estimator."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

AddonCode = Annotated[str, StringConstraints(min_length=1, max_length=60)]


class AddonOut(BaseModel):
    code: str
    label: str
    amount_minor: int
    description: str


class ServiceRuleOut(BaseModel):
    id: UUID
    version_no: int
    currency: str
    base_page_minor: int
    extra_page_minor: int
    revisions_included: int
    lead_time_days: int
    asset_buffer_days: int
    addons: list[AddonOut]
    capabilities: list[str]
    exclusions: list[str]
    notes: str


class EstimateRequest(BaseModel):
    """A hypothetical scope. Extra fields are refused so no amount can ride along."""

    model_config = ConfigDict(extra="forbid")

    pages: int = Field(ge=1, le=20)
    addon_codes: list[AddonCode] = Field(default_factory=list, max_length=20)


class EstimateItemOut(BaseModel):
    code: str
    label: str
    amount_minor: int
    rule_ref: str


class EstimateViolationOut(BaseModel):
    code: str
    detail: str
    rule_ref: str


class EstimateOut(BaseModel):
    rule_version: int
    currency: str
    total_minor: int
    items: list[EstimateItemOut]
    violations: list[EstimateViolationOut]
