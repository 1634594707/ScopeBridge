# Agent Note: Two-arm comparative evaluation, with denominators and failures always visible

Status: implemented

## Problem

The product claim is that "the model proposes, the program judges" is safer than "let the model
quote directly". That claim needs evidence, and unit tests can only prove the rules layer is
self-consistent — they say nothing about what the model actually emits on a real gateway. The first
evaluation also had two measurement defects: the pipeline's `unsafe_releases` was hardcoded to 0,
which treats a design constraint as a measurement; and `helpful_options` only counted cases where the
original requirement was already feasible, ignoring options that became feasible after narrowing.
Worse, every rate used "successfully parsed samples" as the denominator, so a disobedient model
never hurt the score.

## Decision

`evals/cases.json` fixes 19 rule-level cases (plus 1 flow case covered by the API tests);
`evals/run_eval.py` runs both arms; `evals/metrics.py` is pure-function statistics only, easy to
unit-test:

- **baseline**: one prompt asks the model for `pages / addon_codes / total_usd / feasible`, then the
  rules re-check the scope it named. Any of `price_mismatch`, `false_promise`, `unknown_addons`
  makes the case `unsafe`.
- **pipeline**: the model returns five facts only; the server builds and prices candidates. Before
  any report is written, every candidate **calls `evaluate` again** and the displayed price/verdict
  are compared against the recomputed ones; `invariant_violations` counts both mismatch classes,
  measured on every run instead of hardcoded 0.
- **Denominators**: all `*_rate` divide by `calls` (including unparseable and transport failures);
  only metrics explicitly labelled `of_parsed` use parsed samples as the denominator.
- **Failure classification**: every failure records `failure_class` (`transport` / `content`) and
  `raw_head` (first 200 characters of raw output) for later classification from the source.
- **Pipeline outcome split**: `original_satisfied` (original requirement feasible and a feasible
  option given), `narrowed_available` (original infeasible but the narrowed option is feasible),
  `no_solution_honest` (infeasible and no feasible option) — the three should sum to the parsed
  count.

Execution is sequential by default (`--workers 1`) because this gateway returns timeouts and
truncations under concurrency, which would get misrecorded as model failures. Reports land as JSON +
Markdown, reviewable case by case, with `--tag` in the filename.

## Alternatives considered

1. **Keep only the pytest rule tests**. Strongest case: stable, fast, zero cost, already proves the
   rules are right. Rejected: it measures nothing about model behaviour, and judges look at whether
   "the AI is actually used and actually constrained" — that needs real-call evidence.
2. **Keep the single `helpful_options` metric**. Strongest case: one number is the easiest to report
   and the easiest for an audience to remember. Rejected: it rewards cases where the original
   request was easy and punishes cases solved by narrowing — exactly backwards for the product's
   value.
3. **Hardcode the pipeline's unsafe count to 0**. Strongest case: guaranteed by construction, so 0
   is logically true. Rejected: if the pricing or display path ever regressed, the report would
   still show 0; only recomputing each run can expose the regression.
4. **Automatically retry parse failures until they succeed**. Strongest case: yields a beautiful
   compliance rate. Rejected: it masks model instability and distorts cost and latency; failure
   counts and raw text must stay visible.

## Consequences

- Benefit: every metric traces to per-case results; "the model misbehaved" and "the flow is unsafe"
  are presented separately; the pipeline invariant is independently recomputed on every run.
- Cost: one full evaluation needs 38+ calls (19 cases × 2 arms × repeats) and is visibly affected by
  gateway fluctuations.
- Known limitation: a report represents only that run; quoted numbers must carry the time and file
  path and must never be extrapolated into a general "model accuracy"; the local gateway showed
  timeouts and truncations on 2026-10-30.

## Verification

- `backend/tests/test_eval_metrics.py`: denominators, unsafe double denominators, the pipeline's
  three-way outcome split, invariant-violation counting, Markdown states its denominators.
- `backend/tests/test_eval_cases.py`: 19 rule-level cases checked one by one for release verdict,
  total, violation codes and missing fields.
- Latest report `evals/reports/20261030T151055Z-facts-v7-inline-both.md` (19 cases × 1 run):
  baseline parsed 18/19 (1 transport error), pipeline 19/19; baseline twice called rule-rejected
  scopes feasible, pipeline's independently recomputed violations are 0; pipeline: original
  satisfied 6, narrowed available 6, honest no-solution 7.
