"""Wire schemas for the published rule set."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


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
