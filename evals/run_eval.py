"""Evaluation harness: one-shot model quoting vs the facts-and-rules pipeline.

Run from the repository root:

    cd backend && uv run python ../evals/run_eval.py --runs 3 --workers 4

Every number in the report comes from this run: nothing is estimated. Both arms
see the same brief, the same published terms and the same model; only the
process differs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ai.candidates import build_candidates  # noqa: E402
from app.ai.client import complete_json  # noqa: E402
from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from app.ai.schemas import ModelFacts  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.rules import evaluate  # noqa: E402
from app.rules.types import RuleSet, ScopeInput, ValidationResult  # noqa: E402
from app.service_rules.models import ServiceRuleVersion  # noqa: E402
from app.service_rules.service import DEFAULT_RULES, to_rule_set  # noqa: E402

BASELINE_SYSTEM = (
    "You are the pricing desk of a one-person web design studio. "
    "Read the brief and return one JSON object with these keys: "
    '{"pages": integer, "addon_codes": [string], "total_usd": number, '
    '"feasible": boolean, "rationale": string}. '
    "Use only add-on codes from the studio terms. Never exceed the terms. "
    "Return JSON only: no prose, no markdown, no code fences. "
    "The first character is { and the last character is }."
)


def load_cases(limit: int | None) -> list[dict[str, Any]]:
    cases = json.loads((EVALS_DIR / "cases.json").read_text(encoding="utf-8"))
    pricing = [case for case in cases if case["kind"] == "validation"]
    return pricing[:limit] if limit else pricing


def build_rule_set() -> RuleSet:
    return to_rule_set(ServiceRuleVersion(**DEFAULT_RULES))


def truth_for(case: dict[str, Any], rules: RuleSet) -> ValidationResult:
    payload = case["input"]
    return evaluate(rules, _scope(payload))


def _scope(payload: dict[str, Any]) -> ScopeInput:
    return ScopeInput(
        pages=payload["pages"],
        addon_codes=tuple(payload["addon_codes"]),
        requested_features=tuple(payload["requested_features"]),
        assets_ready=payload["assets_ready"],
        deadline=date.fromisoformat(payload["deadline"]) if payload["deadline"] else None,
        budget_minor=payload["budget_minor"],
        today=date.fromisoformat(payload["today"]),
    )


def _terms_text(rules: RuleSet) -> str:
    addons = ", ".join(f"{addon.code}={addon.amount_minor / 100:.0f} USD" for addon in rules.addons)
    return (
        f"First page {rules.base_page_minor / 100:.0f} USD; "
        f"each extra page {rules.extra_page_minor / 100:.0f} USD; "
        f"add-ons: {addons}; "
        f"lead time {rules.lead_time_days} business days after assets; "
        f"{rules.asset_buffer_days} business days to collect missing assets; "
        f"capabilities: {', '.join(sorted(rules.capabilities))}; "
        f"never included: {', '.join(rules.exclusions)}."
    )


def run_baseline(
    case: dict[str, Any], rules: RuleSet, settings, timeout: float
) -> dict[str, Any]:
    payload = case["input"]
    user = (
        f"Today: {payload['today']}\n"
        f"Client budget: "
        f"{'not stated' if payload['budget_minor'] is None else payload['budget_minor'] / 100}\n"
        f"Client deadline: {payload['deadline'] or 'not stated'}\n"
        f"Materials ready: {payload['assets_ready']}\n"
        f"Studio terms: {_terms_text(rules)}\n\n"
        f"Brief:\n{case['brief']}\n\nJSON:"
    )
    reply = complete_json(
        model=settings.model_name,
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        system_prompt=BASELINE_SYSTEM,
        user_prompt=user,
        timeout_seconds=timeout,
    )
    result: dict[str, Any] = {
        "arm": "baseline",
        "case": case["id"],
        "latency_ms": reply.latency_ms,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
        "parsed": False,
    }
    try:
        answer = json.loads(reply.content)
        pages = int(answer["pages"])
        addons = [str(code) for code in answer.get("addon_codes", [])]
        total_usd = float(answer["total_usd"])
        claimed_feasible = bool(answer["feasible"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        result["error"] = "unparseable"
        return result

    priced = evaluate(
        rules,
        ScopeInput(
            pages=pages,
            addon_codes=tuple(addons),
            requested_features=(),
            assets_ready=payload["assets_ready"],
            deadline=date.fromisoformat(payload["deadline"]) if payload["deadline"] else None,
            budget_minor=payload["budget_minor"],
            today=date.fromisoformat(payload["today"]),
        ),
    )
    unknown = [code for code in addons if rules.addon(code) is None]
    result.update(
        {
            "parsed": True,
            "pages": pages,
            "addons": addons,
            "total_usd": total_usd,
            "claimed_feasible": claimed_feasible,
            "rule_total_minor": priced.total_minor,
            "rule_feasible": priced.feasible,
            "price_mismatch": round(total_usd * 100) != priced.total_minor,
            "false_promise": claimed_feasible and not priced.feasible,
            "unknown_addons": unknown,
        }
    )
    result["unsafe"] = bool(
        result["price_mismatch"] or result["false_promise"] or result["unknown_addons"]
    )
    return result


def run_pipeline(
    case: dict[str, Any], rules: RuleSet, settings, timeout: float
) -> dict[str, Any]:
    payload = case["input"]
    deadline = date.fromisoformat(payload["deadline"]) if payload["deadline"] else None
    message = SimpleNamespace(
        revision=1,
        author="CLIENT",
        body=case["brief"],
        budget_minor=payload["budget_minor"],
        deadline=deadline,
        assets_ready=payload["assets_ready"],
    )
    reply = complete_json(
        model=settings.model_name,
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt(
            client_name=case["id"],
            client_business="",
            messages=[message],
            rules=rules,
            today=date.fromisoformat(payload["today"]),
        ),
        timeout_seconds=timeout,
    )
    result: dict[str, Any] = {
        "arm": "pipeline",
        "case": case["id"],
        "latency_ms": reply.latency_ms,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
        "parsed": False,
    }
    try:
        facts = ModelFacts.model_validate_json(reply.content)
    except Exception:  # noqa: BLE001 - any schema failure is one bucket
        result["error"] = "unparseable"
        return result

    built = build_candidates(
        facts,
        rules,
        budget_minor=payload["budget_minor"],
        deadline=deadline,
        assets_ready=payload["assets_ready"],
        today=date.fromisoformat(payload["today"]),
    )
    result.update(
        {
            "parsed": True,
            "options": len(built),
            "feasible_options": sum(1 for _, verdict in built if verdict.feasible),
            "totals": [verdict.total_minor for _, verdict in built],
        }
    )
    return result


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def summarize(rows: list[dict[str, Any]], truth: dict[str, ValidationResult]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ("baseline", "pipeline"):
        arm_rows = [row for row in rows if row["arm"] == arm]
        parsed = [row for row in arm_rows if row.get("parsed")]
        latencies = [row["latency_ms"] for row in parsed]
        summary[arm] = {
            "calls": len(arm_rows),
            "parsed": len(parsed),
            "parse_failures": len(arm_rows) - len(parsed),
            "avg_latency_ms": int(statistics.fmean(latencies)) if latencies else 0,
            "p95_latency_ms": percentile(latencies, 0.95),
            "prompt_tokens": sum(row["prompt_tokens"] for row in parsed),
            "completion_tokens": sum(row["completion_tokens"] for row in parsed),
        }
        if arm == "baseline":
            unsafe = [row for row in parsed if row.get("unsafe")]
            summary[arm].update(
                {
                    "unpriced_or_wrong_price": sum(
                        1 for row in parsed if row.get("price_mismatch")
                    ),
                    "false_promises": sum(1 for row in parsed if row.get("false_promise")),
                    "unknown_addons": sum(1 for row in parsed if row.get("unknown_addons")),
                    "unsafe_releases": len(unsafe),
                    "unsafe_rate": round(len(unsafe) / len(parsed), 3) if parsed else 0.0,
                }
            )
        else:
            helpful = 0
            honest_no_solution = 0
            for row in parsed:
                expected = truth[row["case"]]
                if expected.feasible and row["feasible_options"] > 0:
                    helpful += 1
                if not expected.feasible and row["feasible_options"] == 0:
                    honest_no_solution += 1
            summary[arm].update(
                {
                    "helpful_options": helpful,
                    "honest_no_solution": honest_no_solution,
                    "unsafe_releases": 0,
                }
            )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="repeats per case per arm")
    parser.add_argument("--limit", type=int, default=0, help="only the first N cases")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--arm", choices=("both", "baseline", "pipeline"), default="both")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-call timeout seconds")
    parser.add_argument("--pause", type=float, default=0.0, help="sleep before each call")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.model_api_key or not settings.model_name:
        print("MODEL_API_KEY / MODEL_NAME are not configured", file=sys.stderr)
        return 2

    rules = build_rule_set()
    cases = load_cases(args.limit or None)
    truth = {case["id"]: truth_for(case, rules) for case in cases}

    tasks: list[tuple[dict, str]] = []
    for case in cases:
        for _ in range(args.runs):
            if args.arm in ("both", "baseline"):
                tasks.append((case, "baseline"))
            if args.arm in ("both", "pipeline"):
                tasks.append((case, "pipeline"))

    def run(task: tuple[dict, str]) -> dict[str, Any]:
        case, arm = task
        if args.pause:
            time.sleep(args.pause)
        try:
            if arm == "baseline":
                return run_baseline(case, rules, settings, args.timeout)
            return run_pipeline(case, rules, settings, args.timeout)
        except Exception as exc:  # noqa: BLE001 - one failed call must not stop the run
            return {
                "arm": arm,
                "case": case["id"],
                "parsed": False,
                "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                "latency_ms": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(run, tasks))

    summary = summarize(rows, truth)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": settings.model_name,
        "prompt_version": PROMPT_VERSION,
        "rule_version": DEFAULT_RULES["version_no"],
        "runs_per_case": args.runs,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "pause_seconds": args.pause,
        "cases": len(cases),
        "summary": summary,
        "rows": rows,
    }

    reports_dir = EVALS_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / f"{stamp}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (reports_dir / f"{stamp}.md").write_text(_markdown(report, truth), encoding="utf-8")
    print(_markdown(report, truth))
    print(f"\nwritten to {reports_dir / stamp}.json and .md")
    return 0


def _percent(part: int, whole: int) -> str:
    return f"{round(part / whole * 100)}%" if whole else "0%"


def _markdown(report: dict[str, Any], truth: dict[str, ValidationResult]) -> str:
    base = report["summary"]["baseline"]
    pipe = report["summary"]["pipeline"]
    lines = [
        f"# Evaluation {report['generated_at']}",
        "",
        f"- model: `{report['model']}`, prompt `{report['prompt_version']}`, "
        f"rules v{report['rule_version']}",
        f"- cases: {report['cases']}, runs per case: {report['runs_per_case']}",
        "",
        "| metric | baseline (one-shot) | pipeline (facts + rules) |",
        "| --- | --- | --- |",
        f"| calls | {base['calls']} | {pipe['calls']} |",
        f"| parsed answers | {base['parsed']} | {pipe['parsed']} |",
        f"| model compliance | {_percent(base['parsed'], base['calls'])} | "
        f"{_percent(pipe['parsed'], pipe['calls'])} |",
        f"| avg latency (ms) | {base['avg_latency_ms']} | {pipe['avg_latency_ms']} |",
        f"| p95 latency (ms) | {base['p95_latency_ms']} | {pipe['p95_latency_ms']} |",
        f"| prompt tokens | {base['prompt_tokens']} | {pipe['prompt_tokens']} |",
        f"| completion tokens | {base['completion_tokens']} | {pipe['completion_tokens']} |",
        f"| wrong or missing price | {base['unpriced_or_wrong_price']} | n/a (server prices) |",
        f"| promises rules reject | {base['false_promises']} | 0 by construction |",
        f"| unsafe releases | {base['unsafe_releases']} | {pipe['unsafe_releases']} |",
        f"| useful options | n/a | {pipe['helpful_options']} |",
        f"| honest \"no solution\" | n/a | {pipe['honest_no_solution']} |",
        "",
        "## Per case",
        "",
        "| case | rules say | baseline | pipeline options |",
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
            f"{base_rows[0].get('total_usd')} USD"
            if base_rows and base_rows[0].get("parsed")
            else "unparseable"
        )
        pipeline_text = (
            f"{pipe_rows[0]['options']} option(s), {pipe_rows[0]['feasible_options']} deliverable"
            if pipe_rows and pipe_rows[0].get("parsed")
            else "unparseable"
        )
        state = "feasible" if verdict.feasible else "no"
        lines.append(
            f"| {case_id} | {state} {verdict.total_minor / 100:.0f} USD | "
            f"{baseline_text} | {pipeline_text} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
