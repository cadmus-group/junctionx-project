#!/usr/bin/env bash
# Deterministically reset and regenerate the demo dataset end-to-end.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  uv run --package gridtrace-worker python -m gridtrace_worker.main refresh-demo
else
  PYTHONPATH="apps/worker/src:apps/api/src:packages/domain-py/src" \
    python3 -m gridtrace_worker.main refresh-demo
fi
