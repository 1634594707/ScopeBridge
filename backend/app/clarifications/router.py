"""Clarification endpoints: seller manual note and client confirmation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import UserAuth, require_client_csrf, require_csrf
from app.clarifications import service
from app.clarifications.schemas import (
    ClarificationConfirmRequest,
    ClarificationOut,
    ManualClarificationRequest,
)
from app.core.db import get_db
from app.requirements.service import load_for_client, load_for_seller

router = APIRouter(tags=["clarifications"])


@router.post(
    "/requirements/{requirement_id}/clarifications/manual",
    response_model=ClarificationOut,
    status_code=201,
)
def record_manual_clarification(
    requirement_id: UUID,
    payload: ManualClarificationRequest,
    auth: UserAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ClarificationOut:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    row = service.create_manual_clarification(
        db,
        requirement,
        auth.user.id,
        note=payload.note,
        reason_code=payload.reason_code,
    )
    return service.serialize(row)


@router.post(
    "/portal/requirements/{requirement_id}/clarifications/{clarification_id}/confirm",
    response_model=ClarificationOut,
)
def confirm_clarification(
    requirement_id: UUID,
    clarification_id: UUID,
    payload: ClarificationConfirmRequest,
    auth: UserAuth = Depends(require_client_csrf),
    db: Session = Depends(get_db),
) -> ClarificationOut:
    requirement = load_for_client(db, requirement_id, auth.user.id)
    row = service.confirm_ai_clarification(
        db,
        requirement,
        clarification_id,
        auth.user.id,
        answers=payload.answers,
        acknowledged=payload.acknowledged,
        acknowledged_unsupported=payload.acknowledged_unsupported,
    )
    return service.serialize(row)
