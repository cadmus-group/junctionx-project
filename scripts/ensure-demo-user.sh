#!/usr/bin/env bash
# Restore demo_operator login user (after production ingest or empty users table).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main ensure-demo-user "$@"
