#!/usr/bin/env bash
set -euo pipefail

PROJECT="scopebridge-verify"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.verify.yml"
BACKEND="${REPO_ROOT}/backend"
FRONTEND="${REPO_ROOT}/frontend"

# Process-local overrides only. The repository .env is never written.
export DATABASE_URL="postgresql+psycopg://scopebridge:verify-password@127.0.0.1:55434/scopebridge_verify"
export APP_BASE_URL="http://127.0.0.1:4173"
export SESSION_SECRET="verify-only-session-secret-32-characters"
export SELLER_EMAIL="seller@verify.local"
export SELLER_PASSWORD="verify-seller-password"
export CLIENT_EMAIL="client@verify.local"
export CLIENT_PASSWORD="verify-client-password"
export MODEL_API_KEY="test-model-key"
export MODEL_NAME="test-model"
export PAYPAL_CLIENT_ID="test-client-id"
export PAYPAL_CLIENT_SECRET="test-client-secret"
export PAYPAL_BASE_URL="https://api-m.sandbox.paypal.com"

RESULTS_FILE="$(mktemp)"
trap 'rm -f "${RESULTS_FILE}"' EXIT

run_step() {
  local name="$1"
  local workdir="$2"
  shift 2
  echo
  echo "==> ${name}"
  local started
  started="$(date +%s)"
  (
    cd "${workdir}"
    "$@"
  )
  local finished
  finished="$(date +%s)"
  local seconds=$((finished - started))
  printf '%s\t%s\n' "${name}" "${seconds}" >> "${RESULTS_FILE}"
  echo "OK ${name} (${seconds}s)"
}

wait_for_database() {
  echo
  echo "==> database readiness probe (pg_isready, not sleep)"
  local started
  started="$(date +%s)"
  local ready=0
  for _ in $(seq 1 60); do
    if docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" exec -T db \
      pg_isready -U scopebridge -d scopebridge_verify >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
  done
  if [[ "${ready}" -ne 1 ]]; then
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" logs --tail 30 db || true
    echo "database did not become ready within 120 seconds" >&2
    return 1
  fi
  local finished
  finished="$(date +%s)"
  local seconds=$((finished - started))
  printf 'database readiness\t%s\n' "${seconds}" >> "${RESULTS_FILE}"
  echo "OK database readiness (${seconds}s)"
}

print_summary() {
  echo
  echo "Timing summary"
  awk -F '\t' '{ printf "  %-28s %8ss\n", $1, $2 }' "${RESULTS_FILE}"
  awk -F '\t' '{ total += $2 } END { printf "  %-28s %8ss\n", "total", total }' "${RESULTS_FILE}"
}

on_error() {
  echo
  echo "FAILED: ${1:-unknown step}" >&2
  if [[ -s "${RESULTS_FILE}" ]]; then
    print_summary
  fi
  echo "The isolated stack and its volume were left in place; nothing was deleted." >&2
  exit 1
}
trap 'on_error "unexpected failure"' ERR

run_step "database start" "${REPO_ROOT}" \
  docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" up -d
wait_for_database

run_step "uv sync" "${BACKEND}" uv sync
run_step "alembic upgrade head" "${BACKEND}" uv run alembic upgrade head
run_step "seed demo data" "${BACKEND}" uv run python -m app.seed
run_step "pytest" "${BACKEND}" uv run pytest -q
run_step "ruff" "${BACKEND}" uv run ruff check .
run_step "pnpm install" "${FRONTEND}" pnpm install --frozen-lockfile
run_step "tsc -b" "${FRONTEND}" pnpm exec tsc -b
run_step "vite build" "${FRONTEND}" pnpm exec vite build

trap - ERR
print_summary
echo
echo "All verification steps passed."
echo "Isolated stack: project=${PROJECT}, port=55434, database=scopebridge_verify"
echo "Volume is project-scoped and separate from the demo volume."
echo "Stop it without deleting data:"
echo "  docker compose -f \"${COMPOSE_FILE}\" -p ${PROJECT} stop"
