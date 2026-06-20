#!/usr/bin/env bash
# Build and start the full GridTrace Docker stack (postgres, migrate, api, worker, web).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Creating .env from .env.example — review before production use."
  cp .env.example .env
fi

mkdir -p data/raw data/processed apps/ml-lab/artifacts

docker compose up -d --build "$@"

echo ""
echo "GridTrace stack is starting."
echo "  Web:  http://localhost:${WEB_PORT:-3000}"
echo "  API:  http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "First-time setup:"
echo "  docker compose run --rm worker seed"
echo "  docker compose run --rm worker ingest-dutch-energy   # if Liander CSV present"
echo ""
echo "Logs: docker compose logs -f"
