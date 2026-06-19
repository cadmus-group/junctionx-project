#!/usr/bin/env bash
# Seed deterministic synthetic demo data (grid, readings, features, scores).
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  uv run --package gridtrace-worker python -m gridtrace_worker.main seed
else
  PYTHONPATH="apps/worker/src:apps/api/src:packages/domain-py/src" \
    python3 -m gridtrace_worker.main seed
fi
