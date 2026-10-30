"""Runs the fixed evaluation cases through the rule layer."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.rules import evaluate
from app.rules.types import ScopeInput
from app.service_rules.models import ServiceRuleVersion
from app.service_rules.service import DEFAULT_RULES, to_rule_set

CASES_FILE = Path(__file__).resolve().parents[2] / "evals" / "cases.json"


def _cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def _validation_cases() -> list[dict]:
    return [case for case in _cases() if case["kind"] == "validation"]


def test_twenty_cases_are_defined() -> None:
    assert len(_cases()) == 20
    assert len(_validation_cases()) == 19


@pytest.mark.parametrize("case", _validation_cases(), ids=lambda case: case["id"])
def test_validation_case(case: dict) -> None:
    rules = to_rule_set(ServiceRuleVersion(**DEFAULT_RULES))
    payload = case["input"]
    result = evaluate(
        rules,
        ScopeInput(
            pages=payload["pages"],
            addon_codes=tuple(payload["addon_codes"]),
            requested_features=tuple(payload["requested_features"]),
            assets_ready=payload["assets_ready"],
            deadline=date.fromisoformat(payload["deadline"]) if payload["deadline"] else None,
            budget_minor=payload["budget_minor"],
            today=date.fromisoformat(payload["today"]),
        ),
    )
    expected = case["expected"]
    assert result.feasible is expected["feasible"], case["id"]
    assert result.total_minor == expected["total_minor"], case["id"]
    assert set(result.violation_codes()) == set(expected["violation_codes"]), case["id"]
    assert list(result.missing_fields) == expected["missing_fields"], case["id"]
