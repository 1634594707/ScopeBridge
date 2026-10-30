"""Seller-facing model endpoints. Nothing here can create a quote."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import service
from app.ai.schemas import ExtractionEnvelope, ExtractionOut
from app.api.deps import SellerAuth, require_csrf, require_seller
from app.core.db import get_db
from app.requirements.service import load_for_seller

router = APIRouter(tags=["ai"])


@router.post(
    "/requirements/{requirement_id}/extractions",
    response_model=ExtractionOut,
    status_code=201,
)
def create_extraction(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ExtractionOut:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    return service.extract(db, requirement)


@router.get(
    "/requirements/{requirement_id}/extractions/latest",
    response_model=ExtractionEnvelope,
)
def read_latest_extraction(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> ExtractionEnvelope:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    return ExtractionEnvelope(extraction=service.latest(db, requirement))
