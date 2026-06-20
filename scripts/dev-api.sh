#!/usr/bin/env bash
# Start the FastAPI dev server on port 8003 (kills a stale listener first).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${API_PORT:-8003}"

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "==> Stopping existing process on port $PORT"
  lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.5
fi

cd "$ROOT/apps/api"
export PYTHONPATH="src:../../packages/domain-py/src"
exec "$ROOT/.venv/bin/uvicorn" gridtrace_api.main:app \
  --reload \
  --host 0.0.0.0 \
  --port "$PORT"
