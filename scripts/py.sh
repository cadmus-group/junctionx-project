#!/usr/bin/env bash
# Resolve the Python interpreter for GridTrace scripts.
# Prefers .venv; falls back to python3 on PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -x "$ROOT/.venv/bin/python" ]; then
  echo "$ROOT/.venv/bin/python"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  echo "$ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  echo "python3"
else
  echo "error: no Python interpreter found (run ./scripts/pip-install.sh)" >&2
  exit 1
fi
