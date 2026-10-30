"""Evaluation harness: one-shot model quoting vs the facts-and-rules pipeline.

Run from the backend directory:

    cd backend && uv run python ../evals/run_eval.py --runs 3 --workers 1 --tag baseline

Both arms see the same brief, the same published terms and the same model; only
the process differs. Every number in the report comes from this run, and any
answer that cannot be parsed is recorded as a failure with its head text.
"""

from __future__ import annotations

import argparse
import json
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
sys.path.insert(0, str(EVALS_DIR))

from metrics import render_markdown, summarize  # noqa: E402

from app.ai.candidates import build_candidates  # noqa: E402
from app.ai.client import complete_json  # noqa: E402
from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from app.ai.schemas import ModelFacts  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.errors import ApiError  # noqa: E402
from app.rules import evaluate  # noqa: E402
from app.rules.types import RuleSet, ScopeInput  # noqa: E402
from app.service_rules.models import ServiceRuleVersion  # noqa: E402
from app.service_rules.service import DEFAULT_RULES, to_rule_set  # noqa: E402

METRICS_VERSION = "v2"

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


def truth_for(case: dict[str, Any], rules: RuleSet) -> dict[str, Any]:
    payload = case["input"]
    verdict = evaluate(rules, _scope(payload))
    return {"feasible": verdict.feasible, "total_minor": verdict.total_minor}


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
        BASELINE_SYSTEM
        + "\n\n"
        + f"Today: {payload['today']}\n"
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
    row: dict[str, Any] = {
        "arm": "baseline",
        "case": case["id"],
        "latency_ms": reply.latency_ms,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
        "raw_head": reply.content[:200],
        "parsed": False,
    }
    try:
        answer = json.loads(reply.content)
        pages = int(answer["pages"])
        addons = [str(code) for code in answer.get("addon_codes", [])]
        total_usd = float(answer["total_usd"])
        claimed_feasible = bool(answer["feasible"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        row["failure_class"] = "content"
        row["error"] = "unparseable"
        return row

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
    row.update(
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
    row["unsafe"] = bool(
        row["price_mismatch"] or row["false_promise"] or row["unknown_addons"]
    )
    return row


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
            # A realistic name: passing the case id made the model echo it as a
            # "client" field and answer with a report instead of the fact sheet.
            client_name="Maya Ortiz",
            client_business="",
            messages=[message],
            rules=rules,
            today=date.fromisoformat(payload["today"]),
        ),
        timeout_seconds=timeout,
    )
    row: dict[str, Any] = {
        "arm": "pipeline",
        "case": case["id"],
        "latency_ms": reply.latency_ms,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
        "raw_head": reply.content[:200],
        "parsed": False,
    }
    try:
        facts = ModelFacts.model_validate_json(reply.content)
    except Exception:  # noqa: BLE001 - any schema failure is one bucket
        row["failure_class"] = "content"
        row["error"] = "unparseable"
        return row

    today = date.fromisoformat(payload["today"])
    built = build_candidates(
        facts,
        rules,
        budget_minor=payload["budget_minor"],
        deadline=deadline,
        assets_ready=payload["assets_ready"],
        today=today,
    )
    details = []
    for candidate, verdict in built:
        fresh = evaluate(
            rules,
            ScopeInput(
                pages=candidate.pages,
                addon_codes=tuple(candidate.addon_codes),
                requested_features=tuple(candidate.requested_features),
                assets_ready=payload["assets_ready"],
                deadline=deadline,
                budget_minor=payload["budget_minor"],
                today=today,
            ),
        )
        details.append(
            {
                "label": candidate.label,
                "pages": candidate.pages,
                "addon_codes": list(candidate.addon_codes),
                "requested_features": list(candidate.requested_features),
                "feasible": verdict.feasible,
                "total_minor": verdict.total_minor,
                "price_matches_rules": fresh.total_minor == verdict.total_minor,
                "feasible_matches_rules": fresh.feasible == verdict.feasible,
            }
        )
    row.update(
        {
            "parsed": True,
            "options": len(built),
            "feasible_options": sum(1 for _, verdict in built if verdict.feasible),
            "options_detail": details,
        }
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="repeats per case per arm")
    parser.add_argument("--limit", type=int, default=0, help="only the first N cases")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--arm", choices=("both", "baseline", "pipeline"), default="both")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-call timeout seconds")
    parser.add_argument("--pause", type=float, default=0.0, help="sleep before each call")
    parser.add_argument("--tag", default="", help="label for this run, e.g. prompt-v7")
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
        except ApiError as exc:
            return {
                "arm": arm,
                "case": case["id"],
                "parsed": False,
                "failure_class": "transport",
                "error": f"{exc.code}: {exc.message[:120]}",
                "latency_ms": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
        except Exception as exc:  # noqa: BLE001 - one failed call must not stop the run
            return {
                "arm": arm,
                "case": case["id"],
                "parsed": False,
                "failure_class": "transport",
                "error": f"{type(exc).__name__}: {str(exc)[:120]}",
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
        "metrics_version": METRICS_VERSION,
        "rule_version": DEFAULT_RULES["version_no"],
        "runs_per_case": args.runs,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "pause_seconds": args.pause,
        "tag": args.tag,
        "cases": len(cases),
        "summary": summary,
        "rows": rows,
    }

    reports_dir = EVALS_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    suffix = f"-{args.tag}" if args.tag else ""
    stem = f"{stamp}{suffix}"
    (reports_dir / f"{stem}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    markdown = render_markdown(report, truth)
    (reports_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\nwritten to {reports_dir / stem}.json and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
