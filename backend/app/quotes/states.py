"""Quote state machine.

Four states, four legal moves. Anything else raises 409 instead of being
silently tolerated, so a confirmed quote can never drift back into draft.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.errors import conflict


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"


class QuoteAction(StrEnum):
    REVIEW = "REVIEW"
    CONFIRM = "CONFIRM"
    SUPERSEDE = "SUPERSEDE"


TRANSITIONS: dict[tuple[QuoteStatus, QuoteAction], QuoteStatus] = {
    (QuoteStatus.DRAFT, QuoteAction.REVIEW): QuoteStatus.REVIEWED,
    (QuoteStatus.REVIEWED, QuoteAction.CONFIRM): QuoteStatus.CONFIRMED,
    (QuoteStatus.DRAFT, QuoteAction.SUPERSEDE): QuoteStatus.SUPERSEDED,
    (QuoteStatus.REVIEWED, QuoteAction.SUPERSEDE): QuoteStatus.SUPERSEDED,
}


def transition(current: str, action: QuoteAction) -> QuoteStatus:
    status = QuoteStatus(current)
    target = TRANSITIONS.get((status, action))
    if target is None:
        raise conflict(
            "invalid_transition",
            f"A quote in {status} cannot be moved by {action}.",
            {"from": status, "action": action},
        )
    return target
