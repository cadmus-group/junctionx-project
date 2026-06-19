#!/usr/bin/env bash
# Export the FastAPI OpenAPI schema and regenerate typed TypeScript contracts.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Exporting OpenAPI schema from FastAPI"
if command -v uv >/dev/null 2>&1; then
  uv run --package gridtrace-api python scripts/export-openapi.py
else
  PYTHONPATH="apps/api/src:packages/domain-py/src" python3 scripts/export-openapi.py
fi

echo "==> Generating TypeScript types from OpenAPI"
pnpm --filter @gridtrace/contracts run generate

echo "==> Done. Run 'pnpm typecheck' to validate consumers."
