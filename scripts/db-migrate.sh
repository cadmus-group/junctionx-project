#!/usr/bin/env bash
# Apply database migrations to head.
set -euo pipefail
cd "$(dirname "$0")/../apps/api"

if command -v uv >/dev/null 2>&1; then
  uv run alembic upgrade head
else
  PYTHONPATH="src:../../packages/domain-py/src" alembic upgrade head
fi
