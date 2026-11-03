# Workspace Agent Rules (ScopeBridge)

ScopeBridge is a constrained service-closing assistant: the model may propose, but prices come only
from the rules layer, verdicts come only from the program, and payment is confirmed only by the
client. The rules below serve that goal and every session must follow them.

## 1. Technology decision lookup (SDFrame)

For technical decisions — architecture choices, design patterns, testing strategy, deployment —
consult SDFrame (<https://sdframe.caldis.me/>, unauthenticated static API) before concluding:

- Index: `https://sdframe.caldis.me/api/frameworks.index.json`
- Detail: `https://sdframe.caldis.me/api/frameworks/{slug}.json` (validate the slug against the
  index first)
- Judge by the candidate framework's "fits / does not fit" scenarios and Do's/Don'ts, not by
  impression

## 2. Engineering iron rules (project-specific)

- **Single path, no fallback**: one goal keeps one main path. Silent degradation that makes failure
  "look normal" is forbidden; fail fast and surface a clear reason upward.
- **Amounts have exactly one source**: `app/rules/` is the only place allowed to price. No number in
  model output may reach a quote, and client request bodies must not carry amounts.
- **Response bodies must not leak**: error responses contain only `{code, message, details?}` — no
  tokens, sessions, UIDs, IPs, file paths or raw exception text.
- **Unknown external results always enter RECONCILING**: never treat "unconfirmed" as success or
  failure; only server-verified state may unlock a quote or write a snapshot.
- **Credentials live only in `.env`**: sandbox and model credentials never enter the repository;
  `.env.example` keeps placeholders only.

## 3. Verification and reporting

- Before committing, run: `uv run pytest -q`, `uv run ruff check .`, `pnpm exec tsc -b`,
  `pnpm exec vite build`.
- Completion reports must separate **verified** (with the actual commands and results), **unverified**
  and **blocked items**; planned capability must never be reported as implemented.
- Every quoted evaluation number must carry its report file path and run time; never extrapolate it
  into a general "model accuracy".

## 4. What the repository is allowed to contain

- `README.md` is the single entry point: product, how to run it, API surface, evaluation results,
  known limits. `docs/` holds only the two diagrams it links to and their screenshots.
- Everything in the tree is English. Code comments, commit messages and documentation included.
- No process paperwork: development logs, demo scripts, video notes, submission drafts, compliance
  matrices and decision-note directories stay out of the repository. A reason worth keeping belongs
  in the README or in a comment next to the code that embodies it.
- `.agents/`, `.codebuddy/` and similar agent workspaces are local tooling; they are git-ignored and
  must never be force-added.
