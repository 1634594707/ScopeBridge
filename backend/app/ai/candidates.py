"""Candidate scopes are built here, not invented by the model.

The model supplies facts (pages, budget read, features). Turning those facts
into at most two deliverable options is a deterministic function of the rule
set, so it is testable and cannot drift between model versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ai.schemas import ModelFacts
from app.rules import evaluate
from app.rules.types import RuleSet, ScopeInput, ValidationResult


@dataclass(frozen=True)
class CandidateScope:
    label: str
    pages: int
    addon_codes: tuple[str, ...]
    requested_features: tuple[str, ...]
    rationale: str


def build_candidates(
    facts: ModelFacts,
    rules: RuleSet,
    *,
    budget_minor: int | None,
    deadline: date | None,
    assets_ready: bool,
    today: date,
) -> list[tuple[CandidateScope, ValidationResult]]:
    pages = facts.pages or 1
    features = tuple(facts.features)

    primary = CandidateScope(
        label="As briefed",
        pages=pages,
        addon_codes=(),
        requested_features=features,
        rationale="The brief priced exactly as stated, with no scope removed.",
    )
    primary_result = _price(primary, rules, budget_minor, deadline, assets_ready, today)
    if primary_result.feasible:
        return [(primary, primary_result)]

    supported = tuple(feature for feature in features if feature in rules.capabilities)
    asks_for_ordering = any("order" in feature.lower() for feature in features)
    addons: tuple[str, ...] = ()
    if asks_for_ordering and "external_order_link" in rules.capabilities:
        addons = ("external_order_link",)

    narrowed = CandidateScope(
        label="One-page launch, narrowed to fit",
        pages=1,
        addon_codes=addons,
        requested_features=supported,
        rationale=(
            "A single page with only the capabilities this studio offers, "
            "and an external ordering link instead of an on-site checkout."
        ),
    )
    if (
        narrowed.pages == primary.pages
        and narrowed.requested_features == primary.requested_features
        and narrowed.addon_codes == primary.addon_codes
    ):
        return [(primary, primary_result)]

    narrowed_result = _price(narrowed, rules, budget_minor, deadline, assets_ready, today)
    return [(primary, primary_result), (narrowed, narrowed_result)]


def _price(
    candidate: CandidateScope,
    rules: RuleSet,
    budget_minor: int | None,
    deadline: date | None,
    assets_ready: bool,
    today: date,
) -> ValidationResult:
    return evaluate(
        rules,
        ScopeInput(
            pages=candidate.pages,
            addon_codes=candidate.addon_codes,
            requested_features=candidate.requested_features,
            assets_ready=assets_ready,
            deadline=deadline,
            budget_minor=budget_minor,
            today=today,
        ),
    )
