#!/usr/bin/env bash
# Seed deterministic synthetic demo data (grid, readings, features, scores).
set -euo pipefail
cd "$(dirname "$0")/.."
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main seed "$@"
