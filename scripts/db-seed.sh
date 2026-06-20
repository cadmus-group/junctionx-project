#!/usr/bin/env bash
# Seed deterministic synthetic demo data (grid, readings, features, scores).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash "$(dirname "$0")/db-migrate.sh"
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main seed "$@"
