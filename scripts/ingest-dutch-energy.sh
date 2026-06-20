#!/usr/bin/env bash
# Assign Stedin/Liander zipcodes and street-level baselines to customers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -d "$ROOT/data/raw/stedin" ] && [ -n "$(find "$ROOT/data/raw/stedin" -maxdepth 1 -name 'stedin_kleinverbruik_*.csv' -print -quit)" ]; then
  bash "$(dirname "$0")/setup-stedin-data.sh"
else
  bash "$(dirname "$0")/download-liander.sh"
fi
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main ingest-dutch-energy "$@"
