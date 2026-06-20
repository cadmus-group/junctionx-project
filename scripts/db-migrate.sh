#!/usr/bin/env bash
# Apply database migrations to head.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/api"
PY="$("$ROOT/scripts/py.sh")"

if [ "$PY" = "python3" ] && [ ! -x "$ROOT/.venv/bin/python" ]; then
  PYTHONPATH="src:../../packages/domain-py/src" "$PY" -m alembic upgrade head
else
  "$PY" -m alembic upgrade head
fi
