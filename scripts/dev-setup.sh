#!/usr/bin/env bash
# Bootstrap local dev: JS/Python deps, .env, Postgres, migrations, demo seed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d node_modules ]; then
  echo "==> Installing JS dependencies"
  pnpm install
fi

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

if [ ! -x .venv/bin/uvicorn ]; then
  echo "==> Installing Python dependencies (first run may take a minute)"
  ./scripts/pip-install.sh
fi

echo "==> Starting Postgres"
docker compose up -d --wait postgres

echo "==> Running database migrations"
./scripts/db-migrate.sh

customer_count="$(
  docker exec gridtrace-postgres psql -U gridtrace -d gridtrace -tAc \
    "SELECT COUNT(*) FROM customers" 2>/dev/null | tr -d '[:space:]' || echo "0"
)"
if [ "${customer_count:-0}" = "0" ]; then
  echo "==> Seeding demo data (first run)"
  ./scripts/db-seed.sh
else
  echo "==> Demo data already present ($customer_count customers), skipping seed"
fi

echo "==> Dev environment ready"
