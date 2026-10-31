# Workspace Agent Rules (ScopeBridge)

ScopeBridge is a constrained service-closing assistant: the model may propose, but prices come only
from the rules layer, verdicts come only from the program, and payment is confirmed only by the
client. The rules below serve that goal and every session must follow them.

## 1. Agent notes

Non-trivial changes must leave a note under `.agents/notes/`, following the `write-notes-like-deepseek`
skill conventions (status is the directory: proposed / implemented / rejected / archived; six kinds:
feature, bug-fix, simplification, architecture, process, testing).

1. **Decide whether a change is non-trivial before touching code**: changed behaviour, architecture,
   cross-file contracts, process or toolchain, testing strategy, on-disk/network/config formats —
   any hit requires a note. Purely mechanical changes (formatting, renames, styling) must never get
   a note.
2. **Search existing notes on the same topic before writing a new one**: a change that already has a
   home updates that note in place; a superseded proposal is archived or deleted on the spot.
3. **Abandoned approaches must be written down, starting with their strongest case**, then why they
   were not used.
4. **Run note verification before committing**:

   ```bash
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
   ```

## 2. Technology decision lookup (SDFrame)

For technical decisions — architecture choices, design patterns, testing strategy, deployment —
consult SDFrame (<https://sdframe.caldis.me/>, unauthenticated static API) before concluding:

- Index: `https://sdframe.caldis.me/api/frameworks.index.json`
- Detail: `https://sdframe.caldis.me/api/frameworks/{slug}.json` (validate the slug against the
  index first)
- Judge by the candidate framework's "fits / does not fit" scenarios and Do's/Don'ts, not by
  impression

## 3. Engineering iron rules (project-specific)

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

## 4. Verification and reporting

- Before committing, run: `uv run pytest -q`, `uv run ruff check .`, `pnpm exec tsc -b`,
  `pnpm exec vite build`.
- Completion reports must separate **verified** (with the actual commands and results), **unverified**
  and **blocked items**; planned capability must never be reported as implemented.
- Every quoted evaluation number must carry its report file path and run time; never extrapolate it
  into a general "model accuracy".

## 5. Skills and documents

- Skills under `.agents/skills/` are auxiliary tools and cannot override user authorisation
  boundaries or the iron rules above.
- A skill name appearing in a document does not mean the current host has loaded it; missing skills
  or check tools must be reported, never claimed as executed.
- The project documentation index is `docs/README.md`.
