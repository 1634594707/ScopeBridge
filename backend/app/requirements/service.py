"""Requirement lifecycle: intake, message append, ownership checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
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


def brief_is_closed(db: Session, requirement: Requirement) -> bool:
    """A brief is closed after payment, even if a legacy row still says OPEN."""
    if requirement.status == CLOSED_STATUS:
        return True
    from app.payments.models import OrderSnapshot

    return (
        db.scalar(
            select(OrderSnapshot.id).where(
                OrderSnapshot.requirement_id == requirement.id
            )
        )
        is not None
    )


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
    from app.clarifications.models import RequirementClarification
    from app.payments.models import ACTIVE_STATUSES, OrderSnapshot, PaymentAttempt
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

    payment_evidence = db.scalar(
        select(PaymentAttempt.id).where(
            PaymentAttempt.requirement_id == requirement.id,
            or_(
                PaymentAttempt.status.in_(ACTIVE_STATUSES),
                PaymentAttempt.paypal_order_id.is_not(None),
                PaymentAttempt.paypal_capture_id.is_not(None),
            ),
        )
    )
    if payment_evidence is not None:
        raise conflict(
            "payment_in_progress",
            "This brief has an unresolved or recorded payment attempt. Resolve it "
            "before deleting the brief.",
        )

    quote_version_ids = select(QuoteVersion.id).where(
        QuoteVersion.requirement_id == requirement.id
    )
    db.execute(delete(PaymentAttempt).where(PaymentAttempt.requirement_id == requirement.id))
    db.execute(delete(QuoteItem).where(QuoteItem.quote_version_id.in_(quote_version_ids)))
    db.execute(delete(QuoteVersion).where(QuoteVersion.requirement_id == requirement.id))
    db.execute(
        delete(RequirementClarification).where(
            RequirementClarification.requirement_id == requirement.id
        )
    )
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
    if brief_is_closed(db, requirement):
        raise conflict("brief_closed", "This brief is closed after payment.")
    if payload.expected_revision != requirement.revision:
        raise conflict(
            "revision_conflict",
            "This requirement changed since you loaded it. Reload before writing again.",
            {
                "expected_revision": payload.expected_revision,
                "current_revision": requirement.revision,
            },
        )

    budget = payload.budget_minor
    if budget is None:
        budget = _latest_value(requirement.messages, "budget_minor")
    deadline = payload.deadline
    if deadline is None:
        deadline = _latest_value(requirement.messages, "deadline")
    assets = payload.assets_ready
    if assets is None:
        assets = _latest_value(requirement.messages, "assets_ready")

    updated = db.execute(
        update(Requirement)
        .where(
            Requirement.id == requirement.id,
            Requirement.revision == payload.expected_revision,
        )
        .values(
            revision=Requirement.revision + 1,
            updated_at=datetime.now(UTC),
        )
    )
    if (updated.rowcount or 0) != 1:
        db.rollback()
        current = db.scalar(
            select(Requirement.revision).where(Requirement.id == requirement.id)
        )
        raise conflict(
            "revision_conflict",
            "This requirement changed since you loaded it. Reload before writing again.",
            {
                "expected_revision": payload.expected_revision,
                "current_revision": current,
            },
        )

    message = RequirementMessage(
        requirement_id=requirement.id,
        author=author,
        body=payload.body,
        budget_minor=budget,
        deadline=deadline,
        assets_ready=assets,
        revision=payload.expected_revision + 1,
    )
    db.add(message)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        current = db.scalar(
            select(Requirement.revision).where(Requirement.id == requirement.id)
        )
        raise conflict(
            "revision_conflict",
            "This requirement changed since you loaded it. Reload before writing again.",
            {
                "expected_revision": payload.expected_revision,
                "current_revision": current,
            },
        ) from None
    db.refresh(requirement)
    db.refresh(message)

    from app.quotes import service as quotes_service

    quotes_service.supersede_open(db, requirement.id)
    return message


def _latest_value(messages: list[RequirementMessage], field: str) -> Any:
    """Carry the newest non-null value forward; a seller note must not erase it."""
    for message in reversed(messages):
        value = getattr(message, field, None)
        if value is not None:
            return value
    return None


def latest_client_message(requirement: Requirement) -> RequirementMessage | None:
    return next(
        (message for message in reversed(requirement.messages) if message.author == "CLIENT"),
        None,
    )


def undeletable_requirement_ids(db: Session, requirement_ids: list[UUID]) -> set[UUID]:
    """Briefs that carry a receipt or an unresolved/recorded payment attempt."""
    if not requirement_ids:
        return set()
    from app.payments.models import ACTIVE_STATUSES, OrderSnapshot, PaymentAttempt

    receipt_ids = set(
        db.scalars(
            select(OrderSnapshot.requirement_id).where(
                OrderSnapshot.requirement_id.in_(requirement_ids)
            )
        ).all()
    )
    attempt_ids = set(
        db.scalars(
            select(PaymentAttempt.requirement_id).where(
                PaymentAttempt.requirement_id.in_(requirement_ids),
                or_(
                    PaymentAttempt.status.in_(ACTIVE_STATUSES),
                    PaymentAttempt.paypal_order_id.is_not(None),
                    PaymentAttempt.paypal_capture_id.is_not(None),
                ),
            )
        ).all()
    )
    return receipt_ids | attempt_ids


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
