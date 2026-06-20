#!/usr/bin/env bash
# Seed deterministic demo data inside the worker container.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose run --rm worker seed "$@"
