#!/usr/bin/env bash
# Run API integration tests against the isolated gridtrace_test database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/db-test-setup.sh

export TEST_ASYNC_DATABASE_URL="${TEST_ASYNC_DATABASE_URL:-postgresql+asyncpg://gridtrace:gridtrace@localhost:5432/gridtrace_test}"

exec "$ROOT/.venv/bin/python" -m pytest apps/api/tests/integration/ -v "$@"
