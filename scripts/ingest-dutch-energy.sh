#!/usr/bin/env bash
# Assign Liander zipcodes and street-level baselines to customers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
"$(dirname "$0")/download-liander.sh"
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main ingest-dutch-energy "$@"
