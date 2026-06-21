#!/usr/bin/env bash
# Ingest production CSVs from data/raw/production/ and run the scoring pipeline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash "$(dirname "$0")/setup-production-csv.sh"
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main ingest-production "$@"
