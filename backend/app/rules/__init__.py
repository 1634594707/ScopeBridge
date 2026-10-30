"""Zero-IO decision layer: pricing and feasibility.

Nothing here touches the database, the network or the clock (callers pass
`today`). The same functions will judge model output in M3, so no rule may live
anywhere else.
"""

from app.rules.feasibility import evaluate
from app.rules.pricing import price_scope
from app.rules.types import (
    AddonDefinition,
    ComputedItem,
    RuleSet,
    ScopeInput,
    ValidationResult,
    Violation,
)

__all__ = [
    "AddonDefinition",
    "ComputedItem",
    "RuleSet",
    "ScopeInput",
    "ValidationResult",
    "Violation",
    "evaluate",
    "price_scope",
]
