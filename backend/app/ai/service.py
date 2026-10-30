"""Run one extraction, validate it, then let the server build and price scopes.

Order matters and must not change:
1. the model reads the brief and returns five facts,
2. the schema rejects anything that does not fit that shape,
3. `app.ai.candidates` turns the facts into at most two options,
4. `app.rules.evaluate` prices and judges them. Model-supplied money is only
   ever shown as "what the model read"; it never becomes a quote amount.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import candidates as candidate_builder
from app.ai import client as model_client
from app.ai.models import AiExtraction
from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from app.ai.schemas import (
    ExtractionOut,
    FactsOut,
    ModelFacts,
    PricedCandidateOut,
    RecordOut,
)
from app.core.config import get_settings
from app.core.errors import ApiError
from app.proposals.schemas import ViolationOut
from app.requirements.models import Requirement
from app.requirements.service import latest_client_message
from app.rules.types import RuleSet
from app.service_rules import service as rules_service


def extract(db: Session, requirement: Requirement) -> ExtractionOut:
    settings = get_settings()
    if not settings.model_api_key or not settings.model_name:
        raise ApiError(
            503,
            "model_not_configured",
            "Set MODEL_API_KEY and MODEL_NAME in .env to draft with the model.",
        )
    if not requirement.messages:
        raise ApiError(409, "no_messages", "This brief has no messages to read.")

    rule_row = rules_service.get_active_rules(db)
    rule_set = rules_service.to_rule_set(rule_row)

    try:
        raw, latency_ms = model_client.complete_json(
            model=settings.model_name,
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                client_name=requirement.client_name,
                client_business=requirement.client_business,
                messages=requirement.messages,
                rules=rule_set,
                today=date.today(),
            ),
            timeout_seconds=settings.model_timeout_seconds,
        )
    except ApiError as exc:
        _record(db, requirement, "", None, "ERROR", exc.code, exc.message[:500], 0)
        raise

    try:
        facts = ModelFacts.model_validate_json(raw)
    except ValidationError as exc:
        detail = _error_detail(exc)
        _record(
            db,
            requirement,
            raw,
            None,
            "REJECTED",
            "model_output_invalid",
            json.dumps(detail)[:4000],
            latency_ms,
        )
        raise ApiError(
            422,
            "model_output_invalid",
            "The model answer did not match the agreed fact sheet, so nothing was priced.",
            {"errors": detail},
        ) from exc

    record = _record(
        db, requirement, raw, facts.model_dump(), "OK", None, None, latency_ms
    )
    return _to_out(record, facts, requirement, rule_set)


def latest(db: Session, requirement: Requirement) -> ExtractionOut | None:
    record = db.scalar(
        select(AiExtraction)
        .where(
            AiExtraction.requirement_id == requirement.id,
            AiExtraction.status == "OK",
        )
        .order_by(AiExtraction.created_at.desc())
        .limit(1)
    )
    if record is None or record.parsed_output is None:
        return None
    facts = ModelFacts.model_validate(record.parsed_output)
    rule_row = rules_service.get_active_rules(db)
    return _to_out(record, facts, requirement, rules_service.to_rule_set(rule_row))


def _to_out(
    record: AiExtraction,
    facts: ModelFacts,
    requirement: Requirement,
    rule_set: RuleSet,
) -> ExtractionOut:
    message = latest_client_message(requirement)
    budget_minor = message.budget_minor if message else None
    deadline = message.deadline if message else None
    # Unknown asset state is treated as "not ready" so delivery dates never flatter us.
    assets_ready = bool(message.assets_ready) if message else False

    built = candidate_builder.build_candidates(
        facts,
        rule_set,
        budget_minor=budget_minor,
        deadline=deadline,
        assets_ready=assets_ready,
        today=date.today(),
    )

    return ExtractionOut(
        id=record.id,
        model=record.model,
        prompt_version=record.prompt_version,
        latency_ms=record.latency_ms,
        created_at=record.created_at,
        facts=FactsOut(
            pages=facts.pages,
            budget_usd=facts.budget_usd,
            deadline_days=facts.deadline_days,
            assets_ready=facts.assets_ready,
            features=list(facts.features),
        ),
        record=RecordOut(
            revision=requirement.revision,
            budget_minor=budget_minor,
            deadline=deadline,
            assets_ready=message.assets_ready if message else None,
        ),
        source_message_ids=[str(item) for item in record.input_message_ids],
        unsupported_requests=sorted(set(facts.features) - set(rule_set.capabilities)),
        questions=_questions(budget_minor, deadline, message.assets_ready if message else None),
        candidates=[
            PricedCandidateOut(
                label=candidate.label,
                pages=candidate.pages,
                addon_codes=list(candidate.addon_codes),
                requested_features=list(candidate.requested_features),
                rationale=candidate.rationale,
                feasible=result.feasible,
                total_minor=result.total_minor,
                currency=result.currency,
                violations=[
                    ViolationOut(**asdict(violation)) for violation in result.violations
                ],
            )
            for candidate, result in built
        ],
    )


def _questions(
    budget_minor: int | None, deadline: date | None, assets_ready: bool | None
) -> list[str]:
    """Only questions that actually block a price, derived from our own records."""
    questions: list[str] = []
    if budget_minor is None:
        questions.append("What budget can the studio hold you to?")
    if deadline is None:
        questions.append("What date does the site need to be live?")
    if assets_ready is None:
        questions.append("Do you already have the photos and copy?")
    return questions


def _record(
    db: Session,
    requirement: Requirement,
    raw: str,
    parsed: dict | None,
    status: str,
    error_code: str | None,
    error_detail: str | None,
    latency_ms: int,
) -> AiExtraction:
    settings = get_settings()
    record = AiExtraction(
        requirement_id=requirement.id,
        source_revision=requirement.revision,
        model=settings.model_name or "unset",
        prompt_version=PROMPT_VERSION,
        input_message_ids=[str(message.id) for message in requirement.messages],
        raw_output=raw,
        parsed_output=parsed,
        status=status,
        error_code=error_code,
        error_detail=error_detail,
        latency_ms=latency_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _error_detail(exc: ValidationError) -> list[dict]:
    return [
        {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
        for error in exc.errors(include_url=False)
    ]
