"""Intake (client), seller workspace reads and the client brief pages."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.api.deps import (
    UserAuth,
    require_client,
    require_client_csrf,
    require_csrf,
    require_seller,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.payments import service as payments_service
from app.proposals import service as proposals_service
from app.quotes import service as quotes_service
from app.requirements import service
from app.requirements.schemas import (
    AddMessageRequest,
    IntakeRequest,
    IntakeResponse,
    MessageOut,
    PortalView,
    RequirementDetail,
    RequirementSummary,
    SellerRequirementSummary,
)
from app.service_rules import service as rules_service

router = APIRouter(tags=["requirements"])
settings = get_settings()


def _seller_id(db: Session) -> UUID:
    seller = db.scalar(select(User).where(User.email == settings.seller_email.lower()))
    if seller is None:
        raise ApiError(
            503,
            "seller_missing",
            "The studio account is not seeded. Run the documented seed step.",
        )
    return seller.id


@router.post("/requirements", response_model=IntakeResponse, status_code=201)
def create_requirement(
    payload: IntakeRequest,
    auth: UserAuth = Depends(require_client_csrf),
    db: Session = Depends(get_db),
) -> IntakeResponse:
    requirement = service.create_requirement(db, payload, _seller_id(db), auth.user.id)
    return IntakeResponse(
        requirement_id=requirement.id,
        brief_path=f"/briefs/{requirement.id}",
    )


@router.get("/requirements", response_model=list[SellerRequirementSummary])
def list_requirements(
    limit: int = Query(default=50, ge=1, le=50),
    auth: UserAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> list[SellerRequirementSummary]:
    rows = service.list_for_seller(db, auth.user.id, limit=limit)
    locked = service.undeletable_requirement_ids(db, [row.id for row in rows])
    return [
        service.summarize_for_seller(row, deletable=row.id not in locked)
        for row in rows
    ]


@router.get("/requirements/{requirement_id}", response_model=RequirementDetail)
def read_requirement(
    requirement_id: UUID,
    auth: UserAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> RequirementDetail:
    requirement = service.load_for_seller(db, requirement_id, auth.user.id)
    return RequirementDetail(
        requirement=service.summarize(requirement),
        messages=[service.serialize_message(message) for message in requirement.messages],
    )


@router.delete("/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: UUID,
    auth: UserAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    """Seller-side removal of an unpaid brief and every child row."""
    requirement = service.load_for_seller(db, requirement_id, auth.user.id)
    service.delete_for_seller(db, requirement)
    return Response(status_code=204)


@router.post(
    "/requirements/{requirement_id}/messages",
    response_model=MessageOut,
    status_code=201,
)
def add_seller_message(
    requirement_id: UUID,
    payload: AddMessageRequest,
    auth: UserAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MessageOut:
    requirement = service.load_for_seller(db, requirement_id, auth.user.id)
    message = service.append_message(db, requirement, payload, author="SELLER")
    return service.serialize_message(message)


@router.get("/portal/briefs", response_model=list[RequirementSummary])
def list_client_briefs(
    limit: int = Query(default=50, ge=1, le=50),
    auth: UserAuth = Depends(require_client),
    db: Session = Depends(get_db),
) -> list[RequirementSummary]:
    rows = service.list_for_client(db, auth.user.id, limit=limit)
    return [service.summarize(row) for row in rows]


@router.get("/portal/{requirement_id}", response_model=PortalView)
def read_portal(
    requirement_id: UUID,
    auth: UserAuth = Depends(require_client),
    db: Session = Depends(get_db),
) -> PortalView:
    requirement = service.load_for_client(db, requirement_id, auth.user.id)
    rules = rules_service.get_active_rules(db)
    order = payments_service.snapshot_for_requirement(db, requirement.id)
    return PortalView(
        requirement=service.summarize(requirement),
        messages=[service.serialize_message(message) for message in requirement.messages],
        proposals=proposals_service.list_for_requirement(db, requirement.id),
        quotes=quotes_service.list_for_requirement(db, requirement.id),
        payments=payments_service.list_for_requirement(db, requirement.id),
        order=payments_service.serialize_snapshot(order) if order else None,
        service_rule_version=rules.version_no,
        currency=rules.currency,
    )


@router.post("/portal/{requirement_id}/messages", response_model=MessageOut, status_code=201)
def add_client_message(
    requirement_id: UUID,
    payload: AddMessageRequest,
    auth: UserAuth = Depends(require_client_csrf),
    db: Session = Depends(get_db),
) -> MessageOut:
    requirement = service.load_for_client(db, requirement_id, auth.user.id)
    message = service.append_message(db, requirement, payload, author="CLIENT")
    return service.serialize_message(message)
