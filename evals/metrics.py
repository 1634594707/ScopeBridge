"""Metric definitions for the two-arm evaluation.

Pure functions over the recorded rows, so the numbers can be unit-tested without
calling a model. Every rate names its denominator in the key or in the report:

- `*_rate` always divides by **calls** (including unparseable and failed calls);
- `*_of_parsed` divides by parsed answers only and is labelled that way.

The pipeline's "unsafe release" is not hard-coded: each option stores whether the
displayed price and verdict match an independent recomputation from the rules, so
a regression in the pricing path would show up as a non-zero number.
"""

from __future__ import annotations

from statistics import fmean
from typing import Any


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def percent(part: int, whole: int) -> str:
    return f"{round(part / whole * 100)}%" if whole else "0%"


def summarize(rows: list[dict[str, Any]], truth: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ("baseline", "pipeline"):
        arm_rows = [row for row in rows if row["arm"] == arm]
        parsed = [row for row in arm_rows if row.get("parsed")]
        latencies = [row["latency_ms"] for row in parsed]
        summary[arm] = {
            "calls": len(arm_rows),
            "parsed": len(parsed),
            "parse_rate": round(len(parsed) / len(arm_rows), 3) if arm_rows else 0.0,
            "transport_failures": sum(
                1 for row in arm_rows if row.get("failure_class") == "transport"
            ),
            "content_failures": sum(
                1 for row in arm_rows if row.get("failure_class") == "content"
            ),
            "avg_latency_ms": int(fmean(latencies)) if latencies else 0,
            "p95_latency_ms": percentile(latencies, 0.95),
            "prompt_tokens": sum(row["prompt_tokens"] for row in parsed),
            "completion_tokens": sum(row["completion_tokens"] for row in parsed),
        }

        if arm == "baseline":
            unsafe = [row for row in parsed if row.get("unsafe")]
            summary[arm].update(
                {
                    "price_mismatch": sum(1 for row in parsed if row.get("price_mismatch")),
                    "false_promises": sum(1 for row in parsed if row.get("false_promise")),
                    "unknown_addons": sum(1 for row in parsed if row.get("unknown_addons")),
                    "unsafe_releases": len(unsafe),
                    "unsafe_rate_of_parsed": round(len(unsafe) / len(parsed), 3)
                    if parsed
                    else 0.0,
                    "unsafe_rate_of_calls": round(len(unsafe) / len(arm_rows), 3)
                    if arm_rows
                    else 0.0,
                }
            )
            continue

        original_satisfied = 0
        narrowed_available = 0
        no_solution_honest = 0
        invariant_violations = 0
        options_total = 0
        for row in parsed:
            expected = truth[row["case"]]
            feasible_options = int(row.get("feasible_options", 0))
            options_total += int(row.get("options", 0))
            if expected["feasible"] and feasible_options > 0:
                original_satisfied += 1
            if not expected["feasible"] and feasible_options > 0:
                narrowed_available += 1
            if not expected["feasible"] and feasible_options == 0:
                no_solution_honest += 1
            for option in row.get("options_detail", []):
                if not option.get("price_matches_rules", False):
                    invariant_violations += 1
                if not option.get("feasible_matches_rules", False):
                    invariant_violations += 1

        summary[arm].update(
            {
                "options_total": options_total,
                "invariant_violations": invariant_violations,
                "original_satisfied": original_satisfied,
                "narrowed_available": narrowed_available,
                "no_solution_honest": no_solution_honest,
                "deliverable_option_rate_of_calls": round(
                    (original_satisfied + narrowed_available) / len(arm_rows), 3
                )
                if arm_rows
                else 0.0,
            }
        )
    return summary


def render_markdown(report: dict[str, Any], truth: dict[str, dict[str, Any]]) -> str:
    base = report["summary"]["baseline"]
    pipe = report["summary"]["pipeline"]
    calls = report["summary"]["baseline"]["calls"] or 1
    lines = [
        f"# Evaluation {report['generated_at']}",
        "",
        f"- model: `{report['model']}`, prompt `{report['prompt_version']}`, "
        f"rules v{report['rule_version']}, metrics v2",
        f"- cases: {report['cases']}, runs per case: {report['runs_per_case']}, "
        f"workers: {report.get('workers', 1)}",
        f"- tag: `{report.get('tag', 'none')}`",
        "",
        "| metric | baseline | pipeline | denominator |",
        "| --- | --- | --- | --- |",
        f"| calls | {base['calls']} | {pipe['calls']} | all attempts |",
        f"| parsed answers | {base['parsed']} | {pipe['parsed']} | all attempts |",
        f"| parse rate | {percent(base['parsed'], base['calls'])} | "
        f"{percent(pipe['parsed'], pipe['calls'])} | all attempts |",
        f"| transport failures | {base['transport_failures']} | "
        f"{pipe['transport_failures']} | all attempts |",
        f"| content failures | {base['content_failures']} | "
        f"{pipe['content_failures']} | all attempts |",
        f"| avg latency (ms) | {base['avg_latency_ms']} | {pipe['avg_latency_ms']} | parsed |",
        f"| p95 latency (ms) | {base['p95_latency_ms']} | {pipe['p95_latency_ms']} | parsed |",
        f"| prompt tokens | {base['prompt_tokens']} | {pipe['prompt_tokens']} | parsed |",
        f"| completion tokens | {base['completion_tokens']} | {pipe['completion_tokens']} | parsed |",
        f"| wrong price | {base['price_mismatch']} | n/a | parsed (baseline) |",
        f"| claims rules reject | {base['false_promises']} | n/a | parsed (baseline) |",
        f"| unknown add-ons | {base['unknown_addons']} | n/a | parsed (baseline) |",
        f"| unsafe releases | {base['unsafe_releases']} | {pipe['invariant_violations']} | parsed |",
        f"| original request satisfied | n/a | {pipe['original_satisfied']} | all attempts |",
        f"| narrowed option available | n/a | {pipe['narrowed_available']} | all attempts |",
        f"| honest \"no solution\" | n/a | {pipe['no_solution_honest']} | all attempts |",
        "",
        "Pipeline `unsafe releases` counts option rows whose displayed price or verdict "
        "disagrees with a fresh recomputation from the rules; it is measured every run, "
        "not assumed to be zero. Unparseable answers count as failures in every rate "
        "whose denominator is \"all attempts\".",
        "",
        "## Per case",
        "",
        "| case | rules say | baseline (first run) | pipeline (first run) |",
        "| --- | --- | --- | --- |",
    ]
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in report["rows"]:
        by_case.setdefault(row["case"], []).append(row)
    for case_id, rows in by_case.items():
        verdict = truth[case_id]
        base_rows = [row for row in rows if row["arm"] == "baseline"]
        pipe_rows = [row for row in rows if row["arm"] == "pipeline"]
        baseline_text = (
            f"{base_rows[0].get('total_usd')} USD (claimed feasible: "
            f"{base_rows[0].get('claimed_feasible')})"
            if base_rows and base_rows[0].get("parsed")
            else "unparseable"
        )
        pipeline_text = (
            f"{pipe_rows[0]['options']} option(s), "
            f"{pipe_rows[0]['feasible_options']} deliverable"
            if pipe_rows and pipe_rows[0].get("parsed")
            else "unparseable"
        )
        state = "feasible" if verdict["feasible"] else "no"
        lines.append(
            f"| {case_id} | {state} {verdict['total_minor'] / 100:.0f} USD | "
            f"{baseline_text} | {pipeline_text} |"
        )
    lines.append("")
    lines.append(f"_calls in denominator: {calls} per arm._")
    return "\n".join(lines) + "\n"
