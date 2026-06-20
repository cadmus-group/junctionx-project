#!/usr/bin/env bash
# Run a Python module with the project interpreter and PYTHONPATH fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$("$ROOT/scripts/py.sh")"
MODULE="$1"
shift

if [ "$PY" = "python3" ] && [ ! -x "$ROOT/.venv/bin/python" ]; then
  export PYTHONPATH="$ROOT/apps/worker/src:$ROOT/apps/api/src:$ROOT/packages/domain-py/src:${PYTHONPATH:-}"
fi

exec "$PY" -m "$MODULE" "$@"
