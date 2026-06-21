#!/usr/bin/env sh
set -e
# Railway runs start commands without a shell — use this script as the start command.
exec node apps/web/server.js
