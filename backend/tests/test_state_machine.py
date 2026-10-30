"""The quote state machine rejects every move it does not declare."""

from __future__ import annotations

import pytest

from app.core.errors import ApiError
from app.quotes.states import QuoteAction, QuoteStatus, transition


def test_draft_can_be_reviewed() -> None:
    assert transition(QuoteStatus.DRAFT, QuoteAction.REVIEW) is QuoteStatus.REVIEWED


def test_reviewed_can_be_confirmed() -> None:
    assert transition(QuoteStatus.REVIEWED, QuoteAction.CONFIRM) is QuoteStatus.CONFIRMED


def test_draft_cannot_be_confirmed() -> None:
    with pytest.raises(ApiError) as error:
        transition(QuoteStatus.DRAFT, QuoteAction.CONFIRM)
    assert error.value.status_code == 409
    assert error.value.code == "invalid_transition"


def test_confirmed_quote_is_terminal() -> None:
    for action in (QuoteAction.REVIEW, QuoteAction.CONFIRM, QuoteAction.SUPERSEDE):
        with pytest.raises(ApiError):
            transition(QuoteStatus.CONFIRMED, action)


def test_superseded_quote_is_terminal() -> None:
    for action in (QuoteAction.REVIEW, QuoteAction.CONFIRM, QuoteAction.SUPERSEDE):
        with pytest.raises(ApiError):
            transition(QuoteStatus.SUPERSEDED, action)
