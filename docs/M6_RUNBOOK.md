# M6 runbook: isolated reproduction, Path B data, recording, submission

This is the operational sheet for M6. It does not claim a recorded video or a real user trial;
those remain the user's work.

## 1. One-command clean verification

Files:

- `scripts/docker-compose.verify.yml` — independent compose service, port `55434`, database
  `scopebridge_verify`, project-scoped volume.
- `scripts/verify.ps1` — Windows PowerShell entry point.
- `scripts/verify.sh` — bash entry point for CI/judges.

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

```bash
bash scripts/verify.sh
```

The script:

1. starts `docker compose -p scopebridge-verify -f scripts/docker-compose.verify.yml up -d`;
2. probes readiness with `pg_isready` in a loop (not a fixed sleep);
3. runs `uv sync`;
4. runs `uv run alembic upgrade head`;
5. runs `uv run python -m app.seed`;
6. runs `uv run pytest -q`;
7. runs `uv run ruff check .`;
8. runs `pnpm install --frozen-lockfile`;
9. runs `pnpm exec tsc -b`;
10. runs `pnpm exec vite build`;
11. prints per-step and total seconds, and exits non-zero on the first failure.

Safety:

- The compose project is `scopebridge-verify`; the volume is
  `scopebridge-verify_scopebridge-verify-pgdata`, project-scoped and separate from the demo volume.
- The script never runs `down`, `down -v`, or deletes any volume.
- The repository `.env` is never written. All overrides are process-local environment variables:
  `DATABASE_URL`, `APP_BASE_URL`, `SESSION_SECRET`, seller/client demo credentials, model and PayPal
  test placeholders.
- The script leaves the isolated stack running so a failed run can be inspected. Stop it with:

```powershell
docker compose -f scripts/docker-compose.verify.yml -p scopebridge-verify stop
```

This does not delete the volume.

Runs on this machine (2026-11-02):

- Latest re-run on the existing isolated stack, including `uv sync` and `pnpm install`:
  `30.4s` total; `109 passed, 2 warnings`.
- Earlier cold container/new-volume run (before the dependency steps were added): `40.8s` total.
  Treat the two numbers as different measurements, not a before/after speed claim.

```text
latest: database start 0.4s, readiness 0.2s, uv sync 1.8s, alembic 1.8s, seed 1.2s,
        pytest 16.3s, ruff 0.8s, pnpm install 0.6s, tsc 2.5s, vite build 4.8s, total 30.4s
earlier cold run (before dependency steps): total 40.8s
```

## 2. Path B demo data

Path B needs a clean brief with a confirmed quote. The demo database already holds the recorded
sandbox snapshot (`5UL759133K5843017` / `5AR676939L8640110` / 50000); do not mutate it.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare-demo-pathb.ps1
```

What it does:

- `scripts/create_pathb_db.py` connects to the same PostgreSQL server as `.env` and creates the
  separate database `scopebridge_pathb` if it does not exist.
- `uv run alembic upgrade head` applies the schema to that database.
- `uv run python -m app.seed --pathb` creates the demo seller/client, a clean brief, one proposal,
  one quote, review and client confirmation. Re-running is idempotent: if the client already owns a
  brief in the Path B database, it prints the existing requirement and exits.
- The demo database `scopebridge` and its order snapshot are not modified.

To record Path B without editing `.env`, use a new terminal:

```powershell
$line = Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$env:DATABASE_URL = ($line -replace '/scopebridge', '/scopebridge_pathb')
cd backend
uv run uvicorn app.main:app --port 8000
```

Start the frontend/preview as usual and sign in with `CLIENT_EMAIL` / `CLIENT_PASSWORD`. Path A
uses the normal `.env` `DATABASE_URL` (the demo database with the real snapshot).

## 3. Running without credentials

The full no-model/no-PayPal walkthrough is the “Running without credentials” section in
`README.md`. It reaches the UI and the manual quote/confirm flow; model draft and payment stop with
explicit 503 messages and do not silently degrade. A real payment needs sandbox credentials.

## 4. Recording

Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md). It contains the pre-recording checklist, second-by-second
actions, narration/subtitles, page prewarm, and the `PAYPAL_TIMEOUT_SECONDS` restart order.

The committed build has **no Playwright/E2E suite**. The browser flow is a manual recording/check;
do not write “Playwright verified” in the submission material.

## 5. Submission

Use [SUBMISSION_DRAFT.md](SUBMISSION_DRAFT.md) for the Devpost fields. The draft marks the items only
the user can supply: real trial feedback, team information, video URL, and public repository/About
license confirmation.

## 6. Known limits that must stay in the material

- PayPal sandbox only; no webhooks, refunds, partial captures or unattended reconciliation job.
- Real user trial not run.
- Playwright/E2E not implemented.
- `PAYPAL_MERCHANT_ID` is optional; without it only amount and currency are verified, not the payee.
- Demo price list is fictional configuration, not a market rate.

## 7. Cross-platform status

- `scripts/verify.ps1` is the end-to-end verified entry point on Windows; the latest run is above.
- `scripts/verify.sh` has not been executed end-to-end on this machine because WSL has no
  `/bin/bash`. It was syntax-checked in a Linux container:
  `docker run --rm -v "$PWD:/repo" -w /repo bash:5 bash -n scripts/verify.sh` → `bash -n OK`.
- `.github/workflows/verify.yml` runs the same `bash scripts/verify.sh` on `ubuntu-latest`. The
  workflow is added but has not run here; a green run requires the user to push and enable Actions.
- Do not claim the bash/CI path is verified until that run is green.
