"""Deterministic price construction.

The client never supplies an amount. The API prices the confirmed scope with
these functions and stores the resulting line items together with the rule
version they came from.
"""

from __future__ import annotations

from app.rules.types import ComputedItem, RuleSet, ScopeInput

BASE_PAGE_CODE = "base_page"
EXTRA_PAGE_CODE = "extra_page"


def price_scope(rules: RuleSet, scope: ScopeInput) -> tuple[ComputedItem, ...]:
    items: list[ComputedItem] = []

    if scope.pages >= 1:
        items.append(
            ComputedItem(
                code=BASE_PAGE_CODE,
                label="Landing page (base build)",
                amount_minor=rules.base_page_minor,
                quantity=1,
                rule_ref="rule.base_page",
            )
        )
        if scope.pages > 1:
            extra = scope.pages - 1
            items.append(
                ComputedItem(
                    code=EXTRA_PAGE_CODE,
                    label=f"Additional page x{extra}",
                    amount_minor=rules.extra_page_minor * extra,
                    quantity=extra,
                    rule_ref="rule.extra_page",
                )
            )

    for code in sorted(set(scope.addon_codes)):
        addon = rules.addon(code)
        if addon is None:
            continue
        items.append(
            ComputedItem(
                code=addon.code,
                label=addon.label,
                amount_minor=addon.amount_minor,
                quantity=1,
                rule_ref=f"rule.addon.{addon.code}",
            )
        )

    return tuple(items)


def total_of(items: tuple[ComputedItem, ...]) -> int:
    return sum(item.amount_minor for item in items)
