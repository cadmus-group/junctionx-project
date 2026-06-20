#!/usr/bin/env bash
# Normalize Stedin kleinverbruik CSVs into data/raw/stedin/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="$ROOT/data/raw/stedin"
mkdir -p "$DEST_DIR"

moved=0
for year in 2024 2025 2026; do
  dest="$DEST_DIR/stedin_kleinverbruik_${year}.csv"
  if [ -f "$dest" ]; then
    continue
  fi
  for src in \
    "$ROOT/Stedin kleinverbruikgegevens ${year}.csv" \
    "$ROOT/data/raw/Stedin kleinverbruikgegevens ${year}.csv"; do
    if [ -f "$src" ]; then
      mv "$src" "$dest"
      echo "Installed $dest"
      moved=$((moved + 1))
      break
    fi
  done
done

count="$(find "$DEST_DIR" -maxdepth 1 -name 'stedin_kleinverbruik_*.csv' | wc -l | tr -d ' ')"
if [ "$count" = "0" ]; then
  echo "No Stedin kleinverbruik CSVs found. Place files at:" >&2
  echo "  $ROOT/Stedin kleinverbruikgegevens YYYY.csv" >&2
  echo "or under $DEST_DIR/stedin_kleinverbruik_YYYY.csv" >&2
  exit 1
fi

echo "Stedin datasets ready ($count file(s) in $DEST_DIR)"
