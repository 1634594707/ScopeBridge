"""Creating candidate scopes and letting the client pick one."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found
from app.proposals.models import Proposal
from app.proposals.schemas import ProposalCreate, ProposalOut, ViolationOut
from app.requirements.models import Requirement
from app.requirements.service import brief_is_closed, latest_client_message
from app.rules import evaluate
from app.rules.types import ScopeInput
from app.service_rules import service as rules_service

MAX_PROPOSALS_PER_REVISION = 2


def create_proposal(
    db: Session, requirement: Requirement, payload: ProposalCreate
) -> Proposal:
    if brief_is_closed(db, requirement):
        raise conflict("brief_closed", "This brief is closed after payment.")
    existing_count = len(
        db.scalars(
            select(Proposal.id).where(
                Proposal.requirement_id == requirement.id,
                Proposal.source_revision == requirement.revision,
            )
        ).all()
    )
    if existing_count >= MAX_PROPOSALS_PER_REVISION:
        raise conflict(
            "proposal_limit",
            "This revision already has two candidate scopes. Revise the brief to add more.",
            {"current_revision": requirement.revision, "limit": MAX_PROPOSALS_PER_REVISION},
        )

    rule_row = rules_service.get_active_rules(db)
    rule_set = rules_service.to_rule_set(rule_row)
    latest = latest_client_message(requirement)

    # Client record is authoritative. A seller may record one explicit
    # assumption: that assets are ready even though the client said they are not.
    client_assets = latest.assets_ready if latest and latest.assets_ready is not None else False
    assets_ready = payload.assets_ready if payload.assets_ready is not None else client_assets

    result = evaluate(
        rule_set,
        ScopeInput(
            pages=payload.pages,
            addon_codes=tuple(payload.addon_codes),
            requested_features=tuple(payload.requested_features),
            assets_ready=assets_ready,
            deadline=latest.deadline if latest else None,
            budget_minor=latest.budget_minor if latest else None,
            today=date.today(),
        ),
    )

    proposal = Proposal(
        requirement_id=requirement.id,
        rule_version_id=rule_row.id,
        source_revision=requirement.revision,
        label=payload.label,
        pages=payload.pages,
        addon_codes=list(payload.addon_codes),
        requested_features=list(payload.requested_features),
        assets_ready=assets_ready,
        feasible=result.feasible,
        total_minor=result.total_minor,
        currency=result.currency,
        violations=[asdict(violation) for violation in result.violations],
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def load_proposal(db: Session, proposal_id: UUID) -> Proposal:
    proposal = db.get(Proposal, proposal_id)
    if proposal is None:
        raise not_found("Proposal not found")
    return proposal


def select_proposal(db: Session, requirement: Requirement, proposal_id: UUID) -> Proposal:
    if brief_is_closed(db, requirement):
        raise conflict("brief_closed", "This brief is closed after payment.")
    proposal = load_proposal(db, proposal_id)
    if proposal.requirement_id != requirement.id:
        raise not_found("Proposal not found")
    if not proposal.feasible:
        raise conflict(
            "proposal_not_feasible",
            "A scope that cannot be delivered cannot be selected.",
            {"violations": proposal.violations},
        )
    if proposal.source_revision != requirement.revision:
        raise conflict(
            "revision_conflict",
            "This scope was built for an older revision of the brief.",
            {"source_revision": proposal.source_revision, "current_revision": requirement.revision},
        )

    for other in db.scalars(
        select(Proposal).where(
            Proposal.requirement_id == requirement.id,
            Proposal.id != proposal.id,
            Proposal.selected_at.is_not(None),
        )
    ):
        other.selected_at = None

    proposal.selected_at = datetime.now(UTC)
    db.commit()
    db.refresh(proposal)
    return proposal


def list_for_requirement(db: Session, requirement_id: UUID) -> list[ProposalOut]:
    rows = db.scalars(
        select(Proposal)
        .where(Proposal.requirement_id == requirement_id)
        .order_by(Proposal.created_at)
    ).all()
    return [serialize(row) for row in rows]


def serialize(proposal: Proposal) -> ProposalOut:
    return ProposalOut(
        id=proposal.id,
        requirement_id=proposal.requirement_id,
        source_revision=proposal.source_revision,
        label=proposal.label,
        pages=proposal.pages,
        addon_codes=proposal.addon_codes,
        requested_features=proposal.requested_features,
        assets_ready=proposal.assets_ready,
        feasible=proposal.feasible,
        total_minor=proposal.total_minor,
        currency=proposal.currency,
        violations=[ViolationOut(**violation) for violation in proposal.violations],
        selected_at=proposal.selected_at,
        created_at=proposal.created_at,
    )
