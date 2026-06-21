#!/usr/bin/env bash
# Export the deterministic demo dataset as production CSV files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/scripts/py-module.sh" gridtrace_worker.main export-production-csv "$@"
