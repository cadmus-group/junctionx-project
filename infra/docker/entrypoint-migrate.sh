#!/bin/sh
set -eu
cd /app/apps/api
exec uv run --package gridtrace-api alembic upgrade head
