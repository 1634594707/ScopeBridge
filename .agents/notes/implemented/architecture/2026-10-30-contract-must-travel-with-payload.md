# Agent Note: The output contract must travel with the user message

Status: implemented

## Problem

In the fixed 19-case evaluation, only 7–9 fact extractions parsed (37%–47%); the failures were
almost all the model inventing a project-report structure — `{"client": ..., "project": ...,
"brief_summary": ...}` — wrapped in markdown code fences. The same prompt had succeeded 5/5 on one
long brief earlier, so "the contract is badly written" did not hold.

Investigation found the contract was written only in the system message, and this OpenAI-compatible
gateway (`api.uselunora.com`) never delivered system instructions to the model across repeated
experiments — the model only saw the brief inside the user message and treated it as "a document to
summarise". This also explains earlier observations that "persona-style prompts produced prose":
what was actually ignored was the system channel, not the wording.

## Decision

**The contract appears in both the system and the user message; the user message starts with the
contract and ends with the brief.**

`build_user_prompt()` now returns `SYSTEM_PROMPT + "\n\n" + brief`. The eval script's baseline arm
likewise puts its quoting contract at the front of the user message. Everything else is unchanged:
still one call, no automatic retry, no code-fence stripping, no field-name guessing; any
non-conforming reply is `422 model_output_invalid` with the raw output recorded.

Prompt version is `facts-v7`, measurement basis `metrics v2`.

## Alternatives considered

1. **Make the contract sterner in the system message only** (first v7). Strongest case: no
   duplication, fewer tokens, matches conventional OpenAI usage. Rejected: measured parse rate went
   from 47% to 42%, proving the problem is not wording; tuning wording further optimises the wrong
   layer.
2. **Strip markdown code fences and parse leniently**. Strongest case: a good share of failures were
   "fences + invented schema", and removing fences would rescue some. Rejected: it only fixes
   formatting, not schema drift; worse, it makes "the model ignored the contract" invisible.
3. **Add one repair call (feed the model's output back, ask for the contract shape)**. Strongest
   case: materially higher final usability with measurable failures. Rejected: doubles cost and
   latency; unnecessary now that the contract holds at 100%. If the gateway drifts again, it can be
   re-evaluated as a separate stage.
4. **Change model or provider**. Strongest case: the most direct fix. Rejected: the user explicitly
   scoped this round to optimise, not to switch models; the root cause was the message channel, and
   switching models would mask it.

## Consequences

- Benefit: on the same 19 cases, pipeline parse rate went from 47% to **100%**; baseline also went
  from unusable to 95% (the only failure was a transport error). Prompt cost rises by about 200
  tokens per case.
- Cost: the contract is duplicated in two messages and must be edited in sync (`SYSTEM_PROMPT` is
  the single source; `build_user_prompt` references it directly).
- Known limitation: this is an adaptation to this gateway's behaviour, not a general conclusion; on
  a provider that truly honours system messages the duplicate contract is harmless but slightly
  redundant — worth re-confirming in the evaluation.
- Monitoring: `ai_extractions` keeps every raw output and error code; when parse rate drops, check
  the message channel first, wording second.

## Verification

- `evals/reports/20261030T150712Z-facts-v7-inline.md`: pipeline 19/19 parsed, average 4.1 s.
- `evals/reports/20261030T151055Z-facts-v7-inline-both.md`: baseline 18/19 (1 transport error),
  pipeline 19/19; baseline twice called rule-rejected scopes feasible; the pipeline's independently
  recomputed violation count is 0.
- `backend/tests/test_ai_extraction.py` still covers the contract-rejection paths with mocks (prose,
  extra keys, out-of-range pages).
