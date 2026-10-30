"""Quote endpoints for the seller console and the client portal."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import SellerAuth, require_csrf, require_customer, require_seller
from app.core.db import get_db
from app.core.errors import not_found
from app.quotes import service
from app.quotes.schemas import QuoteCreate, QuoteOut
from app.requirements.models import Requirement
from app.requirements.service import load_for_seller

router = APIRouter(tags=["quotes"])


@router.post(
    "/requirements/{requirement_id}/quotes",
    response_model=QuoteOut,
    status_code=201,
)
def create_quote(
    requirement_id: UUID,
    payload: QuoteCreate,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> QuoteOut:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    quote = service.create_quote(db, requirement, payload, auth.user.id)
    return service.serialize(quote)


@router.get("/requirements/{requirement_id}/quotes", response_model=list[QuoteOut])
def list_quotes(
    requirement_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> list[QuoteOut]:
    requirement = load_for_seller(db, requirement_id, auth.user.id)
    return service.list_for_requirement(db, requirement.id)


@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def read_quote(
    quote_id: UUID,
    auth: SellerAuth = Depends(require_seller),
    db: Session = Depends(get_db),
) -> QuoteOut:
    quote = service.load_for_seller(db, quote_id, auth.user.id)
    return service.serialize(quote)


@router.post("/quotes/{quote_id}/review", response_model=QuoteOut)
def review_quote(
    quote_id: UUID,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> QuoteOut:
    quote = service.load_for_seller(db, quote_id, auth.user.id)
    reviewed = service.review_quote(db, quote, auth.user.id)
    return service.serialize(reviewed)


@router.post("/portal/quotes/{quote_id}/confirm", response_model=QuoteOut)
def confirm_quote(
    quote_id: UUID,
    requirement: Requirement = Depends(require_customer),
    db: Session = Depends(get_db),
) -> QuoteOut:
    quote = service.load_quote(db, quote_id)
    if quote.requirement_id != requirement.id:
        raise not_found("Quote not found")
    confirmed = service.confirm_quote(db, quote, requirement)
    return service.serialize(confirmed)
