"""Requirement intake, seller workspace reads and the client portal."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.api.deps import SellerAuth, require_csrf, require_customer, require_seller
from app.core.config import get_settings
from app.core.db import get_db
from app.proposals import service as proposals_service
from app.quotes import service as quotes_service
from app.requirements import service
from app.requirements.models import Requirement
from app.requirements.schemas import (
    AddMessageRequest,
    IntakeRequest,
    IntakeResponse,
    MessageOut,
    PortalView,
    RequirementDetail,
    RequirementSummary,
)
from app.service_rules import service as rules_service

router = APIRouter(tags=["requirements"])
settings = get_settings()


@router.post("/requirements", response_model=IntakeResponse, status_code=201)
def create_requirement(payload: IntakeRequest, db: Session = Depends(get_db)) -> IntakeResponse:
    seller = db.scalar(select(User).where(User.email == settings.seller_email.lower()))
    if seller is None:
        raise RuntimeError("Seller account is missing; run `uv run python -m app.seed`")
    requirement, portal_token = service.create_requirement(db, payload, seller.id)
    return IntakeResponse(
        requirement_id=requirement.id,
        portal_token=portal_token,
        portal_path=f"/r/{portal_token}",
    )


@router.get("/requirements", response_model=list[RequirementSummary])
def list_requirements(
    limit: int = Query(default=50, ge=1, le=50),
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> list[RequirementSummary]:
    rows = service.list_for_seller(db, auth.user.id, limit=limit)
    return [service.summarize(row) for row in rows]


@router.get("/requirements/{requirement_id}", response_model=RequirementDetail)
def read_requirement(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> RequirementDetail:
    requirement = service.load_for_seller(db, requirement_id, auth.user.id)
    return RequirementDetail(
        requirement=service.summarize(requirement),
        messages=[service.serialize_message(message) for message in requirement.messages],
    )


@router.post(
    "/requirements/{requirement_id}/messages",
    response_model=MessageOut,
    status_code=201,
)
def add_seller_message(
    requirement_id: UUID,
    payload: AddMessageRequest,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MessageOut:
    requirement = service.load_for_seller(db, requirement_id, auth.user.id)
    message = service.append_message(db, requirement, payload, author="SELLER")
    return service.serialize_message(message)


@router.get("/portal", response_model=PortalView)
def read_portal(
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> PortalView:
    rules = rules_service.get_active_rules(db)
    return PortalView(
        requirement=service.summarize(requirement),
        messages=[service.serialize_message(message) for message in requirement.messages],
        proposals=proposals_service.list_for_requirement(db, requirement.id),
        quotes=quotes_service.list_for_requirement(db, requirement.id),
        service_rule_version=rules.version_no,
        currency=rules.currency,
    )


@router.post("/portal/messages", response_model=MessageOut, status_code=201)
def add_client_message(
    payload: AddMessageRequest,
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> MessageOut:
    message = service.append_message(db, requirement, payload, author="CLIENT")
    return service.serialize_message(message)
