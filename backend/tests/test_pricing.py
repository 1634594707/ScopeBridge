"""Price construction is deterministic and lives in one place."""

from __future__ import annotations

from app.rules import price_scope
from app.rules.pricing import total_of
from app.rules.types import RuleSet, ScopeInput
from app.service_rules.models import ServiceRuleVersion
from app.service_rules.service import DEFAULT_RULES, to_rule_set


def build_rules() -> RuleSet:
    return to_rule_set(ServiceRuleVersion(**DEFAULT_RULES))


def test_single_page_is_base_price() -> None:
    items = price_scope(build_rules(), ScopeInput(pages=1))
    assert total_of(items) == 50000
    assert items[0].code == "base_page"


def test_three_pages_cost_seven_hundred_dollars() -> None:
    items = price_scope(build_rules(), ScopeInput(pages=3))
    assert total_of(items) == 70000
    assert [item.code for item in items] == ["base_page", "extra_page"]
    assert items[1].quantity == 2


def test_addons_come_from_the_catalog() -> None:
    items = price_scope(
        build_rules(),
        ScopeInput(pages=1, addon_codes=("copywriting", "external_order_link")),
    )
    by_code = {item.code: item.amount_minor for item in items}
    assert by_code["copywriting"] == 15000
    assert by_code["external_order_link"] == 0
    assert total_of(items) == 65000


def test_unknown_addons_are_not_priced() -> None:
    items = price_scope(build_rules(), ScopeInput(pages=1, addon_codes=("mystery",)))
    assert [item.code for item in items] == ["base_page"]
