#!/usr/bin/env bash
# Restore demo_operator login user (after production ingest or empty users table).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -c "
from gridtrace_worker.db import session_scope
from gridtrace_api.modules.auth.bootstrap import ensure_demo_user

with session_scope() as session:
    user = ensure_demo_user(session)
    print(f'Demo user ready: {user.username} (id={user.id})')
"
