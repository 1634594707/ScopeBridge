"""Clarification gate: model facts must be reviewed before a quote is issued.

The model never prices. This service only records what the client was asked,
whether they answered/acknowledged it, and whether the seller used the explicit
manual exception when the model was unavailable or failed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import AiExtraction
from app.clarifications.models import (
    KIND_AI,
    KIND_MANUAL,
    STATUS_CONFIRMED,
    STATUS_PENDING,
    RequirementClarification,
    clarification_payload,
)
from app.clarifications.schemas import ClarificationOut
from app.core.config import get_settings
from app.core.errors import conflict, not_found, unprocessable
from app.requirements.models import Requirement
from app.requirements.service import brief_is_closed


def latest_for_revision(
    db: Session, requirement_id: UUID, revision: int
) -> RequirementClarification | None:
    return db.scalar(
        select(RequirementClarification)
        .where(
            RequirementClarification.requirement_id == requirement_id,
            RequirementClarification.source_revision == revision,
        )
        .order_by(RequirementClarification.created_at.desc())
        .limit(1)
    )


def create_ai_clarification(
    db: Session,
    requirement: Requirement,
    extraction: AiExtraction,
    *,
    questions: list[str],
    unsupported_requests: list[str],
) -> RequirementClarification:
    row = RequirementClarification(
        requirement_id=requirement.id,
        source_revision=requirement.revision,
        kind=KIND_AI,
        status=STATUS_PENDING,
        extraction_id=extraction.id,
        questions=questions,
        unsupported_requests=unsupported_requests,
        created_by=requirement.seller_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_manual_clarification(
    db: Session,
    requirement: Requirement,
    seller_id: UUID,
    *,
    note: str,
    reason_code: str,
) -> RequirementClarification:
    if brief_is_closed(db, requirement):
        raise conflict("brief_closed", "This brief is closed after payment.")

    latest = latest_for_revision(db, requirement.id, requirement.revision)
    if latest is not None and latest.status == STATUS_PENDING:
        raise conflict(
            "clarification_pending",
            "The model clarification for this revision is still waiting for the client.",
            {"clarification_id": str(latest.id)},
        )
    if latest is not None and latest.status == STATUS_CONFIRMED:
        raise conflict(
            "clarification_already_confirmed",
            "This revision already has a confirmed clarification.",
            {"clarification_id": str(latest.id), "kind": latest.kind},
        )

    settings = get_settings()
    if reason_code == "model_not_configured":
        if settings.model_api_key and settings.model_name:
            raise conflict(
                "model_required",
                "The model is configured. Run the model draft before manual clarification.",
            )
    elif reason_code in {"model_unavailable", "model_output_invalid"}:
        failed = db.scalar(
            select(AiExtraction.id).where(
                AiExtraction.requirement_id == requirement.id,
                AiExtraction.source_revision == requirement.revision,
                AiExtraction.status.in_(("ERROR", "REJECTED")),
            )
        )
        if failed is None:
            raise conflict(
                "model_required",
                "Record a failed model attempt before manual clarification.",
            )
    else:
        raise unprocessable("manual_reason_invalid", "Unknown manual clarification reason.")

    now = datetime.now(UTC)
    row = RequirementClarification(
        requirement_id=requirement.id,
        source_revision=requirement.revision,
        kind=KIND_MANUAL,
        status=STATUS_CONFIRMED,
        questions=[],
        unsupported_requests=[],
        answers="",
        acknowledged=False,
        acknowledged_unsupported=False,
        reason_code=reason_code,
        note=note.strip(),
        created_by=seller_id,
        confirmed_by=seller_id,
        confirmed_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def confirm_ai_clarification(
    db: Session,
    requirement: Requirement,
    clarification_id: UUID,
    client_id: UUID,
    *,
    answers: str,
    acknowledged: bool,
    acknowledged_unsupported: bool,
) -> RequirementClarification:
    row = db.get(RequirementClarification, clarification_id)
    if row is None or row.requirement_id != requirement.id:
        raise not_found("Clarification not found")
    if row.kind != KIND_AI:
        raise conflict("not_ai_clarification", "Manual clarifications are not client-confirmed.")
    if row.status != STATUS_PENDING:
        raise conflict(
            "clarification_not_pending",
            "This clarification is no longer awaiting an answer.",
            {"status": row.status},
        )
    if row.source_revision != requirement.revision:
        raise conflict(
            "revision_changed",
            "The brief changed after this clarification was created.",
            {
                "clarification_revision": row.source_revision,
                "current_revision": requirement.revision,
            },
        )
    if not acknowledged:
        raise unprocessable(
            "clarification_acknowledgement_required",
            "Confirm that you reviewed the model facts and questions.",
        )
    if row.questions and not answers.strip():
        raise unprocessable(
            "clarification_answers_required",
            "Answer the clarification questions before confirming.",
        )
    if row.unsupported_requests and not acknowledged_unsupported:
        raise unprocessable(
            "unsupported_acknowledgement_required",
            "Acknowledge the requested capabilities the studio does not offer.",
        )

    row.answers = answers.strip()
    row.acknowledged = True
    row.acknowledged_unsupported = acknowledged_unsupported
    row.status = STATUS_CONFIRMED
    row.confirmed_by = client_id
    row.confirmed_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return row


def require_confirmed(
    db: Session, requirement: Requirement
) -> RequirementClarification:
    row = latest_for_revision(db, requirement.id, requirement.revision)
    if row is None or row.status != STATUS_CONFIRMED:
        raise conflict(
            "clarification_required",
            "The current revision needs a confirmed clarification before a quote can be issued.",
            {
                "source_revision": requirement.revision,
                "status": row.status if row is not None else "NONE",
                "kind": row.kind if row is not None else None,
            },
        )
    return row


def serialize(row: RequirementClarification | None) -> ClarificationOut | None:
    if row is None:
        return None
    return ClarificationOut(**clarification_payload(row))
