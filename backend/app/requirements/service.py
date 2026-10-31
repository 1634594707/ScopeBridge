"""Requirement lifecycle: intake, message append, ownership checks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import conflict, forbidden, not_found
from app.requirements.models import Requirement, RequirementMessage
from app.requirements.schemas import (
    AddMessageRequest,
    IntakeRequest,
    MessageOut,
    RequirementSummary,
    SellerRequirementSummary,
)

OPEN_STATUS = "OPEN"
CLOSED_STATUS = "CLOSED"


def create_requirement(
    db: Session, payload: IntakeRequest, seller_id: UUID, client_id: UUID
) -> Requirement:
    requirement = Requirement(
        seller_id=seller_id,
        client_id=client_id,
        client_name=payload.client_name,
        client_business=payload.client_business,
        client_email=payload.client_email,
        revision=1,
        status=OPEN_STATUS,
    )
    requirement.messages.append(
        RequirementMessage(
            author="CLIENT",
            body=payload.message,
            budget_minor=payload.budget_minor,
            deadline=payload.deadline,
            assets_ready=payload.assets_ready,
            revision=1,
        )
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def load_for_seller(db: Session, requirement_id: UUID, seller_id: UUID) -> Requirement:
    requirement = db.scalar(
        select(Requirement)
        .where(Requirement.id == requirement_id)
        .options(selectinload(Requirement.messages))
    )
    if requirement is None:
        raise not_found("Requirement not found")
    if requirement.seller_id != seller_id:
        raise forbidden("This requirement belongs to another seller")
    return requirement


def load_for_client(db: Session, requirement_id: UUID, client_id: UUID) -> Requirement:
    requirement = db.scalar(
        select(Requirement)
        .where(Requirement.id == requirement_id)
        .options(selectinload(Requirement.messages))
    )
    if requirement is None:
        raise not_found("Requirement not found")
    if requirement.client_id != client_id:
        raise forbidden("This requirement belongs to another client")
    return requirement


def list_for_client(db: Session, client_id: UUID, limit: int = 50) -> list[Requirement]:
    rows = db.scalars(
        select(Requirement)
        .where(Requirement.client_id == client_id)
        .options(selectinload(Requirement.messages))
        .order_by(Requirement.updated_at.desc())
        .limit(limit)
    ).all()
    return list(rows)


def delete_for_seller(db: Session, requirement: Requirement) -> None:
    """Remove an unpaid brief with every child row, newest dependency first.

    A brief that has been paid carries an order snapshot, and the snapshot is
    the receipt — it must never disappear, so payment blocks the delete.
    """
    from app.payments.models import OrderSnapshot, PaymentAttempt
    from app.proposals.models import Proposal
    from app.quotes.models import QuoteItem, QuoteVersion

    snapshot = db.scalar(
        select(OrderSnapshot.id).where(OrderSnapshot.requirement_id == requirement.id)
    )
    if snapshot is not None:
        raise conflict(
            "payment_completed",
            "This brief has a completed payment. The order snapshot is the "
            "receipt and cannot be deleted.",
        )

    quote_version_ids = select(QuoteVersion.id).where(
        QuoteVersion.requirement_id == requirement.id
    )
    db.execute(delete(PaymentAttempt).where(PaymentAttempt.requirement_id == requirement.id))
    db.execute(delete(QuoteItem).where(QuoteItem.quote_version_id.in_(quote_version_ids)))
    db.execute(delete(QuoteVersion).where(QuoteVersion.requirement_id == requirement.id))
    db.execute(delete(Proposal).where(Proposal.requirement_id == requirement.id))
    db.execute(
        delete(RequirementMessage).where(RequirementMessage.requirement_id == requirement.id)
    )
    db.delete(requirement)
    db.commit()


def list_for_seller(db: Session, seller_id: UUID, limit: int = 50) -> list[Requirement]:
    rows = db.scalars(
        select(Requirement)
        .where(Requirement.seller_id == seller_id)
        .options(selectinload(Requirement.messages))
        .order_by(Requirement.updated_at.desc())
        .limit(limit)
    ).all()
    return list(rows)


def append_message(
    db: Session,
    requirement: Requirement,
    payload: AddMessageRequest,
    author: str,
) -> RequirementMessage:
    if payload.expected_revision != requirement.revision:
        raise conflict(
            "revision_conflict",
            "This requirement changed since you loaded it. Reload before writing again.",
            {
                "expected_revision": payload.expected_revision,
                "current_revision": requirement.revision,
            },
        )

    latest = requirement.messages[-1] if requirement.messages else None
    budget = payload.budget_minor
    if budget is None:
        budget = _previous(latest, "budget_minor")
    deadline = (
        payload.deadline if payload.deadline is not None else _previous(latest, "deadline")
    )
    assets = (
        payload.assets_ready
        if payload.assets_ready is not None
        else _previous(latest, "assets_ready")
    )

    message = RequirementMessage(
        requirement_id=requirement.id,
        author=author,
        body=payload.body,
        budget_minor=budget,
        deadline=deadline,
        assets_ready=assets,
        revision=requirement.revision + 1,
    )
    requirement.revision += 1
    requirement.messages.append(message)
    db.add(message)
    db.commit()
    db.refresh(requirement)
    db.refresh(message)

    from app.quotes import service as quotes_service

    quotes_service.supersede_open(db, requirement.id)
    return message


def _previous(message: RequirementMessage | None, field: str) -> Any:
    """Carry the previous message's value forward when the new one omits it."""
    return getattr(message, field, None)


def latest_client_message(requirement: Requirement) -> RequirementMessage | None:
    return next(
        (message for message in reversed(requirement.messages) if message.author == "CLIENT"),
        None,
    )


def receipt_requirement_ids(db: Session, requirement_ids: list[UUID]) -> set[UUID]:
    """Briefs carrying an order snapshot; the snapshot is the receipt."""
    if not requirement_ids:
        return set()
    from app.payments.models import OrderSnapshot

    return set(
        db.scalars(
            select(OrderSnapshot.requirement_id).where(
                OrderSnapshot.requirement_id.in_(requirement_ids)
            )
        ).all()
    )


def summarize_for_seller(
    requirement: Requirement, *, deletable: bool
) -> SellerRequirementSummary:
    return SellerRequirementSummary(
        **summarize(requirement).model_dump(), deletable=deletable
    )


def summarize(requirement: Requirement) -> RequirementSummary:
    latest = latest_client_message(requirement)
    return RequirementSummary(
        id=requirement.id,
        client_name=requirement.client_name,
        client_business=requirement.client_business,
        revision=requirement.revision,
        status=requirement.status,
        budget_minor=latest.budget_minor if latest else None,
        deadline=latest.deadline if latest else None,
        assets_ready=latest.assets_ready if latest else None,
        message_count=len(requirement.messages),
        created_at=requirement.created_at,
        updated_at=requirement.updated_at,
    )


def serialize_message(message: RequirementMessage) -> MessageOut:
    return MessageOut(
        id=message.id,
        author=message.author,
        body=message.body,
        budget_minor=message.budget_minor,
        deadline=message.deadline,
        assets_ready=message.assets_ready,
        revision=message.revision,
        created_at=message.created_at,
    )
