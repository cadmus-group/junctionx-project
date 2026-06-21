#!/usr/bin/env bash
# Prepare production CSV files under data/raw/production/.
#
# Priority:
# 1. Keep existing large datasets (meter_readings.csv with 1000+ rows).
# 2. Otherwise export the full deterministic demo dataset (same physics as db:seed).
# 3. Fall back to *.csv.example templates or test fixtures for schema-only setups.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/data/raw/production"
FIXTURES="$ROOT/apps/worker/tests/fixtures/production"
mkdir -p "$DIR"

copied=0
for example in "$DIR"/*.csv.example; do
  [ -f "$example" ] || continue
  target="${example%.example}"
  if [ ! -f "$target" ]; then
    cp "$example" "$target"
    echo "==> Created $(basename "$target") from example"
    copied=$((copied + 1))
  fi
done

if [ ! -f "$DIR/operators.csv" ] && [ -d "$FIXTURES" ]; then
  echo "==> Copying minimal schema fixtures from tests"
  cp "$FIXTURES"/*.csv "$DIR"/
fi

needs_export=0
if [ "${FORCE_EXPORT_PRODUCTION:-0}" = "1" ]; then
  needs_export=1
elif [ ! -f "$DIR/meter_readings.csv" ]; then
  needs_export=1
else
  row_count="$(wc -l < "$DIR/meter_readings.csv" | tr -d '[:space:]')"
  if [ "${row_count:-0}" -lt 1000 ]; then
    needs_export=1
  fi
fi

if [ "$needs_export" -eq 1 ]; then
  echo "==> Exporting full deterministic demo dataset to data/raw/production/"
  "$ROOT/scripts/py-module.sh" gridtrace_worker.main export-production-csv "$@"
  echo "==> Full production CSVs ready (edit files here to load your real operational data)"
  exit 0
fi

if [ "$copied" -gt 0 ]; then
  echo "==> Schema templates copied. Run pnpm db:export-production for the full demo dataset."
else
  echo "==> Production CSVs already present in data/raw/production/"
fi
