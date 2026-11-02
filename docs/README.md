# Documentation index

The English entry point for judges and developers is the root [`README.md`](../README.md). This
directory holds the design documents, diagrams, demo script and screenshots.

## Current documents

| File | Contents | Status |
| --- | --- | --- |
| [`FORMAL_PROPOSAL.md`](FORMAL_PROPOSAL.md) | Formal proposal v3.0: positioning, users, flow, technology choices, API, state machines, milestones, evaluation, submission checklist | Current (goals and acceptance criteria) |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Development record: milestone status, layout, data model, implemented API, states and recovery, model contract, evaluation, deviations from the plan | Current (updated as the code changes) |
| [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | Demo script: second-by-second actions, narration/subtitles, pre-record checklist, failure injection and restart order | Current |
| [`M6_RUNBOOK.md`](M6_RUNBOOK.md) | M6 operations: isolated one-command verification, Path B data, recording and submission ownership | Current |
| [`SUBMISSION_COMPLIANCE.md`](SUBMISSION_COMPLIANCE.md) | Requirement-by-requirement compliance table, demo/AI/video decisions, deployment minimums, ownership | Current |
| [`SUBMISSION_DRAFT.md`](SUBMISSION_DRAFT.md) | Devpost fields in Chinese/English, required-item checklist, screenshot mapping, user-owned gaps | Draft |
| [`architecture.html`](architecture.html) / [`architecture.json`](architecture.json) | Technical architecture diagram (interactive HTML + source data) | Current |
| [`workflow.html`](workflow.html) / [`workflow.json`](workflow.json) | Business workflow diagram | Current |
| [`screenshots/`](screenshots/) | UI, payment and recovery screenshots, numbered 01–24 | Current |
| [`archive/`](archive/) | Superseded historical documents | Archived |

## Archived documents

| File | Note |
| --- | --- |
| `archive/PROJECT_PLAN-v2.md` | Project plan v2.0, superseded by FORMAL_PROPOSAL v3.0; kept only as the pre-work baseline |

Intermediate artifacts of diagram validation (browser snapshots, validation/receipt JSON) and
proposal-review screenshots are not tracked; only the final diagrams and their source data are kept.

## Reading order

1. Quick product overview and how to run it: root `README.md`
2. Design goals and acceptance criteria: `FORMAL_PROPOSAL.md`
3. Taking over development: `DEVELOPMENT.md`
4. Clean verification, Path B data and recording: `M6_RUNBOOK.md`
5. Recording the demo: `DEMO_SCRIPT.md`
6. Devpost draft and required items: `SUBMISSION_DRAFT.md`
7. Decision rationale: `.agents/notes/implemented/` (architecture, testing and bug-fix notes)
