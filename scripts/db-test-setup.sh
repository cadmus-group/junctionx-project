#!/usr/bin/env bash
# Create an isolated PostgreSQL database for API integration tests.
# Never run integration tests against the dev "gridtrace" database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONTAINER="${POSTGRES_CONTAINER:-gridtrace-postgres}"
TEST_DB="${TEST_DATABASE_NAME:-gridtrace_test}"
PGUSER="${POSTGRES_USER:-gridtrace}"

if ! docker exec "$CONTAINER" pg_isready -U "$PGUSER" -d gridtrace >/dev/null 2>&1; then
  echo "==> Starting Postgres"
  docker compose up -d --wait postgres
fi

exists="$(
  docker exec "$CONTAINER" psql -U "$PGUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${TEST_DB}'" | tr -d '[:space:]'
)"

if [ "$exists" != "1" ]; then
  echo "==> Creating database ${TEST_DB}"
  docker exec "$CONTAINER" psql -U "$PGUSER" -d postgres -c \
    "CREATE DATABASE ${TEST_DB} OWNER ${PGUSER};"
else
  echo "==> Database ${TEST_DB} already exists"
fi

echo "==> Enabling PostGIS on ${TEST_DB}"
docker exec "$CONTAINER" psql -U "$PGUSER" -d "$TEST_DB" -c \
  "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS pgcrypto;"

echo "==> Applying migrations to ${TEST_DB}"
(
  cd "$ROOT/apps/api"
  DATABASE_URL="postgresql://${PGUSER}:${PGUSER}@localhost:5432/${TEST_DB}" \
  ASYNC_DATABASE_URL="postgresql+asyncpg://${PGUSER}:${PGUSER}@localhost:5432/${TEST_DB}" \
  "$ROOT/.venv/bin/alembic" upgrade head
)

echo "==> Test database ready: postgresql://gridtrace:gridtrace@localhost:5432/${TEST_DB}"
