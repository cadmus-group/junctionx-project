#!/usr/bin/env bash
# Deterministically reset and regenerate the demo dataset end-to-end.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "$(dirname "$0")/py-module.sh" gridtrace_worker.main refresh-demo "$@"
