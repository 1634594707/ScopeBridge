"""Seller-authored candidate scopes and the client's selection."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import SellerAuth, require_csrf, require_customer, require_seller
from app.core.db import get_db
from app.proposals import service
from app.proposals.schemas import ProposalCreate, ProposalOut
from app.requirements.models import Requirement
from app.requirements.service import load_for_seller

router = APIRouter(tags=["proposals"])


@router.post(
    "/requirements/{requirement_id}/proposals",
    response_model=ProposalOut,
    status_code=201,
)
def create_proposal(
    requirement_id: UUID,
    payload: ProposalCreate,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ProposalOut:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    proposal = service.create_proposal(db, requirement, payload)
    return service.serialize(proposal)


@router.get("/requirements/{requirement_id}/proposals", response_model=list[ProposalOut])
def list_proposals(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> list[ProposalOut]:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    return service.list_for_requirement(db, requirement.id)


@router.post("/portal/proposals/{proposal_id}/select", response_model=ProposalOut)
def select_proposal(
    proposal_id: UUID,
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> ProposalOut:
    proposal = service.select_proposal(db, requirement, proposal_id)
    return service.serialize(proposal)
