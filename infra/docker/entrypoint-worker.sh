#!/bin/sh
set -eu
exec uv run --package gridtrace-worker python -m gridtrace_worker.main "${@:-scheduler}"
