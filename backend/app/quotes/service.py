"""Quote construction, review and client confirmation."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, not_found
from app.proposals.service import load_proposal
from app.quotes.models import QuoteItem, QuoteVersion
from app.quotes.schemas import QuoteCreate, QuoteItemOut, QuoteOut
from app.quotes.states import QuoteAction, QuoteStatus, transition
from app.requirements.models import Requirement
from app.requirements.service import latest_client_message
from app.rules import evaluate
from app.rules.types import ScopeInput
from app.service_rules import service as rules_service
from app.service_rules.models import ServiceRuleVersion

QUOTE_VALIDITY = timedelta(days=14)


def create_quote(
    db: Session,
    requirement: Requirement,
    payload: QuoteCreate,
    seller_id: UUID,
) -> QuoteVersion:
    proposal = load_proposal(db, payload.proposal_id)
    if proposal.requirement_id != requirement.id:
        raise not_found("Proposal not found")
    if not proposal.feasible:
        raise conflict("proposal_not_feasible", "This scope was rejected by the rule check.")

    rule_row = db.get(ServiceRuleVersion, proposal.rule_version_id)
    if rule_row is None:
        raise not_found("The rule version this scope was priced with no longer exists")

    latest = latest_client_message(requirement)
    rule_set = rules_service.to_rule_set(rule_row)
    result = evaluate(
        rule_set,
        ScopeInput(
            pages=proposal.pages,
            addon_codes=tuple(proposal.addon_codes),
            requested_features=tuple(proposal.requested_features),
            assets_ready=proposal.assets_ready,
            deadline=latest.deadline if latest else None,
            budget_minor=latest.budget_minor if latest else None,
            today=date.today(),
        ),
    )
    if not result.feasible:
        raise conflict(
            "scope_no_longer_feasible",
            "The brief changed and this scope no longer passes the rule check.",
            {"violations": [violation.__dict__ for violation in result.violations]},
        )
    if proposal.source_revision != requirement.revision:
        raise conflict(
            "revision_conflict",
            "This scope was built for an older revision of the brief.",
            {"source_revision": proposal.source_revision, "current_revision": requirement.revision},
        )

    supersede_open(db, requirement.id)

    next_number = int(
        db.scalar(
            select(func.coalesce(func.max(QuoteVersion.quote_number), 0)).where(
                QuoteVersion.requirement_id == requirement.id
            )
        )
        or 0
    ) + 1

    quote = QuoteVersion(
        requirement_id=requirement.id,
        proposal_id=proposal.id,
        rule_version_id=rule_row.id,
        quote_number=next_number,
        source_revision=requirement.revision,
        currency=result.currency,
        total_minor=result.total_minor,
        status=QuoteStatus.DRAFT,
        scope_summary=payload.scope_summary or f"{proposal.label} · {proposal.pages} page(s)",
        expires_at=datetime.now(UTC) + QUOTE_VALIDITY,
    )

    position = 0
    for item in result.items:
        quote.items.append(
            QuoteItem(
                position=position,
                code=item.code,
                label=item.label,
                amount_minor=item.amount_minor,
                rule_ref=item.rule_ref,
                source_message_id=latest.id if latest else None,
                included=True,
            )
        )
        position += 1

    for exclusion in rule_set.exclusions:
        quote.items.append(
            QuoteItem(
                position=position,
                code="exclusion",
                label=exclusion,
                amount_minor=0,
                rule_ref="rule.exclusion",
                source_message_id=None,
                included=False,
            )
        )
        position += 1

    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


def review_quote(db: Session, quote: QuoteVersion, seller_id: UUID) -> QuoteVersion:
    quote.status = transition(quote.status, QuoteAction.REVIEW)
    quote.reviewed_by = seller_id
    quote.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(quote)
    return quote


def confirm_quote(db: Session, quote: QuoteVersion, requirement: Requirement) -> QuoteVersion:
    if quote.requirement_id != requirement.id:
        raise not_found("Quote not found")
    if quote.source_revision != requirement.revision:
        raise conflict(
            "revision_changed",
            "The brief changed after this quote was issued. Ask for an updated quote.",
            {"quote_revision": quote.source_revision, "current_revision": requirement.revision},
        )
    if quote.expires_at is not None and quote.expires_at <= datetime.now(UTC):
        raise conflict("quote_expired", "This quote has expired. Ask for a fresh one.")

    quote.status = transition(quote.status, QuoteAction.CONFIRM)
    quote.confirmed_at = datetime.now(UTC)
    db.commit()
    db.refresh(quote)
    return quote


def supersede_open(db: Session, requirement_id: UUID) -> None:
    rows = db.scalars(
        select(QuoteVersion).where(
            QuoteVersion.requirement_id == requirement_id,
            QuoteVersion.status.in_([QuoteStatus.DRAFT, QuoteStatus.REVIEWED]),
        )
    ).all()
    if not rows:
        return
    now = datetime.now(UTC)
    for row in rows:
        row.status = transition(row.status, QuoteAction.SUPERSEDE)
        row.superseded_at = now
    db.commit()


def load_quote(db: Session, quote_id: UUID) -> QuoteVersion:
    quote = db.get(QuoteVersion, quote_id)
    if quote is None:
        raise not_found("Quote not found")
    return quote


def load_for_seller(db: Session, quote_id: UUID, seller_id: UUID) -> QuoteVersion:
    quote = db.get(QuoteVersion, quote_id)
    if quote is None:
        raise not_found("Quote not found")
    requirement = db.get(Requirement, quote.requirement_id)
    if requirement is None or requirement.seller_id != seller_id:
        raise forbidden("This quote belongs to another seller")
    return quote


def list_for_requirement(db: Session, requirement_id: UUID) -> list[QuoteOut]:
    rows = db.scalars(
        select(QuoteVersion)
        .where(QuoteVersion.requirement_id == requirement_id)
        .order_by(QuoteVersion.quote_number.desc())
    ).all()
    return [serialize(row) for row in rows]


def serialize(quote: QuoteVersion) -> QuoteOut:
    return QuoteOut(
        id=quote.id,
        requirement_id=quote.requirement_id,
        proposal_id=quote.proposal_id,
        quote_number=quote.quote_number,
        source_revision=quote.source_revision,
        currency=quote.currency,
        total_minor=quote.total_minor,
        status=quote.status,
        scope_summary=quote.scope_summary,
        reviewed_at=quote.reviewed_at,
        confirmed_at=quote.confirmed_at,
        superseded_at=quote.superseded_at,
        expires_at=quote.expires_at,
        created_at=quote.created_at,
        items=[
            QuoteItemOut(
                id=item.id,
                position=item.position,
                code=item.code,
                label=item.label,
                amount_minor=item.amount_minor,
                rule_ref=item.rule_ref,
                source_message_id=item.source_message_id,
                included=item.included,
            )
            for item in quote.items
        ],
    )
