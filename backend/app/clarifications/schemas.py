"""Clarification wire schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ClarificationOut(BaseModel):
    id: UUID
    requirement_id: UUID
    source_revision: int
    kind: str
    status: str
    questions: list[str]
    unsupported_requests: list[str]
    answers: str
    acknowledged: bool
    acknowledged_unsupported: bool
    reason_code: str | None
    note: str
    confirmed_at: datetime | None
    created_at: datetime


class ManualClarificationRequest(BaseModel):
    note: str = Field(min_length=10, max_length=500)
    reason_code: Literal[
        "model_not_configured",
        "model_unavailable",
        "model_output_invalid",
    ]


class ClarificationConfirmRequest(BaseModel):
    answers: str = Field(default="", max_length=4000)
    acknowledged: bool
    acknowledged_unsupported: bool = False
