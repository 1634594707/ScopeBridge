# Evaluation

Two things live here: the fixed case set, and the scripts that run them into reports.

## Case set `cases.json`

20 cases: 19 `validation` (run against the rules layer directly by pytest and the eval script) and
1 `flow` (covered by the API tests; the `covered_by` field says where).

| Field | Meaning |
| --- | --- |
| `kind` | `validation` runs `app.rules.evaluate`; `flow` runs through an API test |
| `brief` | The client's original wording, shown to the model; the eval script builds its prompt from it |
| `input` | Rules-layer input, with `today` fixed for reproducibility |
| `expected` | Expected release verdict, total in cents, violation-code set, missing fields |

Coverage: missing information, over-budget, unoffered capability, deadline conflict, add-on pushing
past budget, unknown add-on, zero pages, exactly at budget, exactly at deadline, stacked problems,
requirement change.

```bash
cd backend
uv run pytest tests/test_eval_cases.py -q
```

## Eval script `run_eval.py` and metrics `metrics.py`

Two arms, same cases, same rules, same model:

| Arm | Approach | What is observed |
| --- | --- | --- |
| `baseline` | One prompt asks the model directly for pages + add-ons + total + feasibility claim | Whether price matches the rules, and whether it calls infeasible scopes feasible |
| `pipeline` | The model returns five facts only; the server builds and prices candidates | Whether the original request is satisfied, whether the narrowed option is feasible, whether "no solution" is said honestly |

Metric definitions (`metrics.py`, pure functions, unit-testable):

- Every rate's denominator is the **call count** (including unparseable and transport failures);
  parsed-only samples are used only where explicitly labelled `of_parsed`.
- The pipeline's "unsafe releases" are **recomputed at runtime by calling `evaluate` again**, not
  hardcoded zero.
- Every failure records a `failure_class` (`transport` / `content`) and the first 200 characters of
  raw output, so failures can be classified from the source.

```bash
cd backend
uv run python ../evals/run_eval.py --runs 1 --workers 1 --timeout 90 --pause 1 --tag facts-v7
```

Common flags: `--runs` (repeats per case), `--limit` (first N cases only), `--workers` (default 1 —
concurrency times the gateway out), `--timeout`, `--pause` (seconds between calls), `--arm`
(`both` / `baseline` / `pipeline`), `--tag` (report suffix).

Output goes to `evals/reports/<timestamp>[-<tag>].json` and a matching `.md`, with per-case
verdicts, average/P95 latency and token usage.

When a rule changes, update the case expectations first, then the implementation; never loosen an
assertion to make the script pass. Evaluation methodology and conclusions:
`../.agents/notes/implemented/testing/2026-10-30-comparative-evaluation.md`.
