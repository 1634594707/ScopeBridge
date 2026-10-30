"""Value objects shared by the pricing and feasibility functions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

BUDGET_EXCEEDED = "budget_exceeded"
CAPABILITY_UNAVAILABLE = "capability_unavailable"
UNKNOWN_ADDON = "unknown_addon"
DEADLINE_CONFLICT = "deadline_conflict"
INVALID_SCOPE = "invalid_scope"


@dataclass(frozen=True)
class AddonDefinition:
    code: str
    label: str
    amount_minor: int
    description: str = ""


@dataclass(frozen=True)
class RuleSet:
    currency: str
    base_page_minor: int
    extra_page_minor: int
    revisions_included: int
    lead_time_days: int
    asset_buffer_days: int
    addons: tuple[AddonDefinition, ...] = field(default_factory=tuple)
    capabilities: frozenset[str] = field(default_factory=frozenset)
    exclusions: tuple[str, ...] = field(default_factory=tuple)

    def addon(self, code: str) -> AddonDefinition | None:
        return next((item for item in self.addons if item.code == code), None)


@dataclass(frozen=True)
class ScopeInput:
    pages: int
    addon_codes: tuple[str, ...] = ()
    requested_features: tuple[str, ...] = ()
    assets_ready: bool = True
    deadline: date | None = None
    budget_minor: int | None = None
    today: date = date.today()


@dataclass(frozen=True)
class ComputedItem:
    code: str
    label: str
    amount_minor: int
    quantity: int
    rule_ref: str


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str
    rule_ref: str


@dataclass(frozen=True)
class ValidationResult:
    feasible: bool
    items: tuple[ComputedItem, ...]
    total_minor: int
    currency: str
    violations: tuple[Violation, ...] = ()
    missing_fields: tuple[str, ...] = ()

    def violation_codes(self) -> tuple[str, ...]:
        return tuple(violation.code for violation in self.violations)
