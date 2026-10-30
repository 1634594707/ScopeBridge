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

CASES_DIR = Path(__file__).resolve().parents[2] / "evals" / "cases"
CASES = sorted(CASES_DIR.glob("*.json"))


def _load(case_path: Path) -> dict:
    return json.loads(case_path.read_text(encoding="utf-8"))


def _validation_cases() -> list[dict]:
    return [case for path in CASES if (case := _load(path))["kind"] == "validation"]


def test_five_cases_are_defined() -> None:
    assert len(CASES) == 5


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
    assert result.feasible is expected["feasible"]
    assert result.total_minor == expected["total_minor"]
    assert set(result.violation_codes()) == set(expected["violation_codes"])
    assert list(result.missing_fields) == expected["missing_fields"]
