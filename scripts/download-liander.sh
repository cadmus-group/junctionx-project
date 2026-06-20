#!/usr/bin/env bash
# Download liander_electricity_01012020.csv from Kaggle (lucabasa/dutch-energy).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export ROOT
DEST="$ROOT/data/raw/liander_electricity_01012020.csv"
PY="$("$ROOT/scripts/py.sh")"

if [ -f "$DEST" ]; then
  echo "Already present: $DEST"
  exit 0
fi

mkdir -p "$ROOT/data/raw"

"$PY" <<'PY'
import kagglehub
import os
import shutil
from pathlib import Path

root = Path(os.environ["ROOT"])
dest = root / "data/raw/liander_electricity_01012020.csv"
dataset_path = kagglehub.dataset_download("lucabasa/dutch-energy")

matches = []
for dirpath, _, files in os.walk(dataset_path):
    for name in files:
        if name == "liander_electricity_01012020.csv":
            matches.append(Path(dirpath) / name)

if not matches:
    raise SystemExit(f"liander_electricity_01012020.csv not found under {dataset_path}")

shutil.copy2(matches[0], dest)
print(f"Saved {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
PY
