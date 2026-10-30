"""The evaluation report must count failures, not hide them."""

from __future__ import annotations

import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"
sys.path.insert(0, str(EVALS_DIR))

from metrics import percent, percentile, render_markdown, summarize  # noqa: E402

TRUTH = {
    "case-feasible": {"feasible": True, "total_minor": 50000},
    "case-blocked": {"feasible": False, "total_minor": 70000},
}


def _baseline(case: str, parsed: bool, unsafe: bool = False, failure: str | None = None) -> dict:
    row = {
        "arm": "baseline",
        "case": case,
        "parsed": parsed,
        "latency_ms": 1000,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }
    if not parsed:
        row["failure_class"] = failure or "content"
    else:
        row.update({"unsafe": unsafe, "price_mismatch": False, "false_promise": unsafe})
    return row


def _pipeline(
    case: str, parsed: bool, options: int = 1, feasible: int = 0, violations: int = 0
) -> dict:
    row = {
        "arm": "pipeline",
        "case": case,
        "parsed": parsed,
        "latency_ms": 900,
        "prompt_tokens": 20,
        "completion_tokens": 8,
    }
    if not parsed:
        row["failure_class"] = "content"
        return row
    row.update(
        {
            "options": options,
            "feasible_options": feasible,
            "options_detail": [
                {"price_matches_rules": True, "feasible_matches_rules": True}
                for _ in range(options)
            ],
        }
    )
    for option in row["options_detail"][:violations]:
        option["price_matches_rules"] = False
    return row


def test_rates_use_all_calls_as_denominator() -> None:
    rows = [
        _baseline("case-feasible", parsed=True),
        _baseline("case-blocked", parsed=False, failure="transport"),
    ]
    summary = summarize(rows, TRUTH)["baseline"]
    assert summary["calls"] == 2
    assert summary["parsed"] == 1
    assert summary["parse_rate"] == 0.5
    assert summary["transport_failures"] == 1
    assert summary["content_failures"] == 0


def test_baseline_unsafe_is_reported_against_two_denominators() -> None:
    rows = [
        _baseline("case-feasible", parsed=True, unsafe=False),
        _baseline("case-blocked", parsed=True, unsafe=True),
        _baseline("case-blocked", parsed=False),
    ]
    summary = summarize(rows, TRUTH)["baseline"]
    assert summary["unsafe_releases"] == 1
    assert summary["unsafe_rate_of_parsed"] == 0.5
    assert summary["unsafe_rate_of_calls"] == 0.333


def test_pipeline_splits_outcomes_instead_of_one_helpful_number() -> None:
    rows = [
        _pipeline("case-feasible", parsed=True, options=1, feasible=1),
        _pipeline("case-blocked", parsed=True, options=2, feasible=1),
        _pipeline("case-blocked", parsed=True, options=1, feasible=0),
        _pipeline("case-feasible", parsed=False),
    ]
    summary = summarize(rows, TRUTH)["pipeline"]
    assert summary["calls"] == 4
    assert summary["original_satisfied"] == 1
    assert summary["narrowed_available"] == 1
    assert summary["no_solution_honest"] == 1
    assert summary["deliverable_option_rate_of_calls"] == 0.5


def test_pipeline_invariant_violations_are_counted_not_assumed_zero() -> None:
    rows = [
        _pipeline("case-feasible", parsed=True, options=2, feasible=1, violations=1),
        _pipeline("case-blocked", parsed=True, options=1, feasible=0),
    ]
    summary = summarize(rows, TRUTH)["pipeline"]
    assert summary["invariant_violations"] == 1


def test_markdown_states_the_denominator() -> None:
    rows = [_baseline("case-feasible", parsed=True), _pipeline("case-feasible", parsed=True)]
    report = {
        "generated_at": "2026-10-30T00:00:00Z",
        "model": "test-model",
        "prompt_version": "facts-v6",
        "rule_version": 1,
        "cases": 1,
        "runs_per_case": 1,
        "tag": "unit",
        "summary": summarize(rows, TRUTH),
        "rows": rows,
    }
    markdown = render_markdown(report, TRUTH)
    assert "metrics v2" in markdown
    assert "all attempts" in markdown
    assert "measured every run" in markdown


def test_percentile_and_percent_helpers() -> None:
    assert percentile([], 0.95) == 0
    assert percentile([100, 200, 300, 400], 0.95) == 400
    assert percent(1, 4) == "25%"
    assert percent(0, 0) == "0%"
