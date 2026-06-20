#!/bin/sh
set -eu
PORT="${API_PORT:-8000}"
exec uv run --package gridtrace-api uvicorn gridtrace_api.main:app \
  --host "${API_HOST:-0.0.0.0}" \
  --port "${PORT}"
