#!/usr/bin/env bash
# Install Python workspace packages into .venv using pip (editable installs).
#
# Usage:
#   ./scripts/pip-install.sh          # base packages + dev tools
#   INSTALL_ML=1 ./scripts/pip-install.sh   # also install MOMENT extras (torch, momentfm, duckdb)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      major="${version%%.*}"
      minor="${version#*.}"
      if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
        PYTHON="$candidate"
        break
      fi
    fi
  done
fi

if [ -z "$PYTHON" ]; then
  echo "error: Python 3.11+ required (install via Homebrew: brew install python@3.12)" >&2
  exit 1
fi

VENV="$ROOT/.venv"
echo "==> Using $PYTHON ($("$PYTHON" --version))"

if [ ! -d "$VENV" ]; then
  echo "==> Creating virtualenv at .venv"
  "$PYTHON" -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing workspace packages (editable)"
python -m pip install -e packages/domain-py
python -m pip install -e apps/api
python -m pip install -e apps/worker
python -m pip install -e apps/ml-lab

echo "==> Installing dev tools"
python -m pip install ruff mypy pytest pytest-asyncio

if [ "${INSTALL_ML:-0}" = "1" ]; then
  echo "==> Installing MOMENT ML extras (torch, momentfm, duckdb)"
  python -m pip install -e "apps/worker[ml]"
fi

echo "==> Done. Activate with: source .venv/bin/activate"
