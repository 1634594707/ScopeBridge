"""Quote state machine.

Six states, seven legal moves. Anything else raises 409 instead of being
silently tolerated, so a paid quote can never drift back into draft.

The payment states are part of the same machine on purpose: a quote that is
being paid for cannot be superseded, and a quote only unlocks when the server
has positively verified that no capture succeeded.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.errors import conflict


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    PAYMENT_LOCKED = "PAYMENT_LOCKED"
    PAID = "PAID"
    SUPERSEDED = "SUPERSEDED"


class QuoteAction(StrEnum):
    REVIEW = "REVIEW"
    CONFIRM = "CONFIRM"
    LOCK_FOR_PAYMENT = "LOCK_FOR_PAYMENT"
    MARK_PAID = "MARK_PAID"
    UNLOCK_AFTER_FAILURE = "UNLOCK_AFTER_FAILURE"
    SUPERSEDE = "SUPERSEDE"


TRANSITIONS: dict[tuple[QuoteStatus, QuoteAction], QuoteStatus] = {
    (QuoteStatus.DRAFT, QuoteAction.REVIEW): QuoteStatus.REVIEWED,
    (QuoteStatus.REVIEWED, QuoteAction.CONFIRM): QuoteStatus.CONFIRMED,
    (QuoteStatus.CONFIRMED, QuoteAction.LOCK_FOR_PAYMENT): QuoteStatus.PAYMENT_LOCKED,
    (QuoteStatus.PAYMENT_LOCKED, QuoteAction.MARK_PAID): QuoteStatus.PAID,
    (QuoteStatus.PAYMENT_LOCKED, QuoteAction.UNLOCK_AFTER_FAILURE): QuoteStatus.CONFIRMED,
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


def is_open(status: str) -> bool:
    """Draft or reviewed: a newer brief may still replace it."""
    return status in {QuoteStatus.DRAFT, QuoteStatus.REVIEWED}
