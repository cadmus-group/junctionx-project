#!/usr/bin/env bash
# Install Python workspace packages into .venv using pip (editable installs).
#
# Usage:
#   ./scripts/pip-install.sh
#       Fast path: domain + api + worker + dev tools (~1–2 min)
#
#   INSTALL_ML=1 ./scripts/pip-install.sh
#       Also install MOMENT extras: torch, momentfm, duckdb (~5–15 min download)
#
#   INSTALL_ML_LAB=1 ./scripts/pip-install.sh
#       Also install apps/ml-lab (CatBoost/LightGBM/SHAP — slow, optional)
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

PIP="python -m pip install --progress-bar on"

echo "==> Upgrading pip"
python -m pip install --upgrade pip setuptools wheel

echo "==> [1/4] gridtrace-domain"
$PIP -e packages/domain-py

echo "==> [2/4] gridtrace-api"
$PIP -e apps/api

echo "==> [3/4] gridtrace-worker"
$PIP -e apps/worker

if [ "${INSTALL_ML_LAB:-0}" = "1" ]; then
  echo "==> [optional] gridtrace-ml-lab (CatBoost/LightGBM — may take several minutes)"
  $PIP -e apps/ml-lab
else
  echo "==> Skipping ml-lab (set INSTALL_ML_LAB=1 to include)"
fi

echo "==> [4/4] dev tools"
$PIP ruff mypy pytest pytest-asyncio

if [ "${INSTALL_ML:-0}" = "1" ]; then
  echo "==> [MOMENT] Installing torch + momentfm (large download, please wait)"
  "$(dirname "$0")/pip-install-ml.sh"
fi

echo ""
echo "==> Done. Activate with:"
echo "    source .venv/bin/activate"
if [ "${INSTALL_ML:-0}" != "1" ]; then
  echo ""
  echo "For MOMENT scoring, run:"
  echo "    INSTALL_ML=1 ./scripts/pip-install.sh"
  echo "    # then set MOMENT_ENABLED=true in .env"
fi
