"""Feasibility judgement.

The result is deliberately verbose: the UI has to explain *why* a request cannot
be met, and a quote may only be built from a feasible verdict.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.rules.pricing import price_scope, total_of
from app.rules.types import (
    BUDGET_EXCEEDED,
    CAPABILITY_UNAVAILABLE,
    DEADLINE_CONFLICT,
    INVALID_SCOPE,
    UNKNOWN_ADDON,
    ComputedItem,
    RuleSet,
    ScopeInput,
    ValidationResult,
    Violation,
)

_WEEKEND = {5, 6}


def add_business_days(start: date, days: int) -> date:
    """Advance by whole business days, skipping Saturday and Sunday."""
    cursor = start
    remaining = days
    while remaining > 0:
        cursor += timedelta(days=1)
        if cursor.weekday() not in _WEEKEND:
            remaining -= 1
    return cursor


def format_minor(amount_minor: int, currency: str = "USD") -> str:
    sign = "-" if amount_minor < 0 else ""
    units, cents = divmod(abs(amount_minor), 100)
    symbol = "$" if currency == "USD" else ""
    return f"{sign}{symbol}{units:,}.{cents:02d}"


def earliest_delivery(rules: RuleSet, scope: ScopeInput) -> date:
    start = scope.today
    if not scope.assets_ready:
        start = add_business_days(start, rules.asset_buffer_days)
    return add_business_days(start, rules.lead_time_days)


def evaluate(rules: RuleSet, scope: ScopeInput) -> ValidationResult:
    violations: list[Violation] = []
    missing_fields: list[str] = []

    if scope.pages < 1:
        violations.append(
            Violation(
                code=INVALID_SCOPE,
                detail="A scope needs at least one page.",
                rule_ref="rule.base_page",
            )
        )

    for feature in sorted(set(scope.requested_features)):
        if feature not in rules.capabilities:
            violations.append(
                Violation(
                    code=CAPABILITY_UNAVAILABLE,
                    detail=f"'{feature}' is not a service this practice offers.",
                    rule_ref="rule.capability",
                )
            )

    for code in sorted(set(scope.addon_codes)):
        if rules.addon(code) is None:
            violations.append(
                Violation(
                    code=UNKNOWN_ADDON,
                    detail=f"Unknown add-on '{code}'.",
                    rule_ref="rule.addon",
                )
            )

    items: tuple[ComputedItem, ...] = price_scope(rules, scope)
    total = total_of(items)

    if scope.budget_minor is None:
        missing_fields.append("budget_minor")
    elif total > scope.budget_minor:
        violations.append(
            Violation(
                code=BUDGET_EXCEEDED,
                detail=(
                    f"Scope totals {format_minor(total, rules.currency)} against a budget of "
                    f"{format_minor(scope.budget_minor, rules.currency)}; "
                    f"short by {format_minor(total - scope.budget_minor, rules.currency)}."
                ),
                rule_ref="rule.budget",
            )
        )

    if scope.deadline is None:
        missing_fields.append("deadline")
    else:
        earliest = earliest_delivery(rules, scope)
        if scope.deadline < earliest:
            violations.append(
                Violation(
                    code=DEADLINE_CONFLICT,
                    detail=(
                        f"Earliest delivery is {earliest.isoformat()} "
                        f"(lead time {rules.lead_time_days} business days"
                        + (
                            f" plus {rules.asset_buffer_days} days to collect assets"
                            if not scope.assets_ready
                            else ""
                        )
                        + f"); requested date is {scope.deadline.isoformat()}."
                    ),
                    rule_ref="rule.lead_time",
                )
            )

    return ValidationResult(
        feasible=not violations and not missing_fields,
        items=items,
        total_minor=total,
        currency=rules.currency,
        violations=tuple(violations),
        missing_fields=tuple(missing_fields),
    )
