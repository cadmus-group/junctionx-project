#!/usr/bin/env bash
# Apply database migrations to head.
set -euo pipefail
cd "$(dirname "$0")/../apps/api"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$("$ROOT/scripts/py.sh")"

if [ "$PY" = "python3" ] && [ ! -x "$ROOT/.venv/bin/python" ]; then
  PYTHONPATH="src:../../packages/domain-py/src" "$PY" -m alembic upgrade head
else
  "$PY" -m alembic upgrade head
fi
