"""Feasibility verdicts: the demo story must be reproducible in tests."""

from __future__ import annotations

from datetime import date, timedelta

from app.rules import evaluate
from app.rules.feasibility import add_business_days, earliest_delivery
from app.rules.types import BUDGET_EXCEEDED, CAPABILITY_UNAVAILABLE, DEADLINE_CONFLICT
from app.service_rules.models import ServiceRuleVersion
from app.service_rules.service import DEFAULT_RULES, to_rule_set

TODAY = date(2026, 10, 30)


def build_rules():
    return to_rule_set(ServiceRuleVersion(**DEFAULT_RULES))


def test_three_pages_against_a_five_hundred_budget_is_rejected() -> None:
    result = evaluate(
        build_rules(),
        _scope(pages=3, budget_minor=50000, deadline=TODAY + timedelta(days=30)),
    )
    assert result.total_minor == 70000
    assert result.feasible is False
    assert BUDGET_EXCEEDED in result.violation_codes()
    assert "short by $200.00" in result.violations[0].detail


def test_same_scope_passes_at_seven_hundred() -> None:
    result = evaluate(
        build_rules(),
        _scope(pages=3, budget_minor=70000, deadline=TODAY + timedelta(days=30)),
    )
    assert result.feasible is True
    assert result.missing_fields == ()


def test_on_site_ordering_is_not_a_capability() -> None:
    result = evaluate(
        build_rules(),
        _scope(
            pages=1,
            budget_minor=50000,
            deadline=TODAY + timedelta(days=30),
            requested_features=("landing_pages", "on_site_ordering"),
        ),
    )
    assert result.feasible is False
    assert CAPABILITY_UNAVAILABLE in result.violation_codes()


def test_external_order_link_is_a_capability() -> None:
    result = evaluate(
        build_rules(),
        _scope(
            pages=1,
            budget_minor=50000,
            deadline=TODAY + timedelta(days=30),
            requested_features=("landing_pages", "external_order_link"),
            addon_codes=("external_order_link",),
        ),
    )
    assert result.feasible is True
    assert result.total_minor == 50000


def test_deadline_shorter_than_lead_time_is_rejected_when_assets_are_missing() -> None:
    result = evaluate(
        build_rules(),
        _scope(
            pages=1,
            budget_minor=50000,
            deadline=TODAY + timedelta(days=5),
            assets_ready=False,
        ),
    )
    assert result.feasible is False
    assert DEADLINE_CONFLICT in result.violation_codes()
    assert "collect assets" in result.violations[0].detail


def test_lead_time_starts_after_assets_arrive() -> None:
    rules = build_rules()
    scope = _scope(pages=1, budget_minor=50000, deadline=None, assets_ready=False)
    assert earliest_delivery(rules, scope) == add_business_days(TODAY, 8)


def test_business_days_skip_the_weekend() -> None:
    assert add_business_days(date(2026, 10, 30), 5) == date(2026, 11, 6)


def test_missing_budget_and_deadline_are_reported_not_guessed() -> None:
    result = evaluate(build_rules(), _scope(pages=1, budget_minor=None, deadline=None))
    assert result.feasible is False
    assert result.missing_fields == ("budget_minor", "deadline")


def _scope(
    pages: int,
    budget_minor: int | None,
    deadline: date | None,
    *,
    assets_ready: bool = True,
    addon_codes: tuple[str, ...] = (),
    requested_features: tuple[str, ...] = (),
):
    from app.rules.types import ScopeInput

    return ScopeInput(
        pages=pages,
        addon_codes=addon_codes,
        requested_features=requested_features,
        assets_ready=assets_ready,
        deadline=deadline,
        budget_minor=budget_minor,
        today=TODAY,
    )
