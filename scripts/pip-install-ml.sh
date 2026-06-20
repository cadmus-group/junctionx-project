#!/usr/bin/env bash
# Install only MOMENT ML extras into an existing .venv (no ml-lab).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "error: .venv not found — run ./scripts/pip-install.sh first" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$ROOT/.venv/bin/activate"

PIP="python -m pip install --progress-bar on"

echo "==> Installing build tooling (setuptools, wheel)"
$PIP --upgrade pip setuptools wheel

echo "==> Pre-installing numpy>=2.0 (binary wheel)"
$PIP "numpy>=2.0"

echo "==> Installing torch (large download — 5–15 min)"
$PIP "torch>=2.2"

echo "==> Installing momentfm from GitHub (PyPI pins numpy==1.25.2, broken on Python 3.12)"
$PIP "git+https://github.com/moment-timeseries-foundation-model/moment.git"

echo "==> Installing pyarrow (required by DuckDB → Polars bridge)"
$PIP "pyarrow>=15.0"

echo "==> Verifying imports"
python -c "import torch, numpy, momentfm, pyarrow, duckdb; print('torch', torch.__version__, '| numpy', numpy.__version__)"

echo "==> Done. Set MOMENT_ENABLED=true in .env, then:"
echo "    source .venv/bin/activate"
echo "    python -m gridtrace_worker.main score-moment"
