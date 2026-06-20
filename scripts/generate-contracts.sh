#!/usr/bin/env bash
# Export the FastAPI OpenAPI schema and regenerate typed TypeScript contracts.
set -euo pipefail
cd "$(dirname "$0")/.."

ROOT="$(pwd)"
PY="$("$ROOT/scripts/py.sh")"

echo "==> Exporting OpenAPI schema from FastAPI"
if [ "$PY" = "python3" ] && [ ! -x "$ROOT/.venv/bin/python" ]; then
  PYTHONPATH="apps/api/src:packages/domain-py/src" "$PY" scripts/export-openapi.py
else
  "$PY" scripts/export-openapi.py
fi

echo "==> Generating TypeScript types from OpenAPI"
pnpm --filter @gridtrace/contracts run generate

echo "==> Done. Run 'pnpm typecheck' to validate consumers."
