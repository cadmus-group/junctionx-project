# GridTrace

> Find where energy disappears, explain why, and prioritize what to inspect.

GridTrace detects **probable non-technical electricity losses** (theft, meter
tampering, faults) using consumption analytics, machine learning, grid energy
reconciliation, GIS clustering, explainability, and inspection prioritization.

This is a **hackathon MVP**: a Turborepo monorepo with a modular-monolith FastAPI
backend, a background worker, an ML lab, and a Next.js operator console. It runs
fully offline with deterministic synthetic data.

> ⚠️ **Ethics:** GridTrace produces *operational signals to prioritize inspection*,
> never accusations. All data here is **synthetic**. Confirmation always requires a
> human field inspection. The frontend never computes the authoritative risk score.

## Architecture

```
                       ┌────────────────────────────────────────────┐
                       │                Turborepo                    │
                       └────────────────────────────────────────────┘
  apps/web (Next.js)  ──HTTP──▶  apps/api (FastAPI, modular monolith)
        │  typed @gridtrace/api-client            │
        │  generated @gridtrace/contracts         ▼
        │                              PostgreSQL 15 + PostGIS
        ▼                                          ▲
  MapLibre + deck.gl + ECharts        apps/worker (ingest, synthetic,
                                       features, scoring, hotspots)
                                                   │
                                       apps/ml-lab (train, evaluate,
                                       explain, publish artifacts)

  Shared formulas: packages/domain-py (Python) — single source of truth.
```

- **Backend** is a modular monolith (`modules/<feature>/{router,service,repository,schemas}`)
  with a **separate worker process** for heavy jobs. No microservices, no Kubernetes.
- **Contracts** flow one way: FastAPI OpenAPI → `packages/contracts` → `packages/api-client` → web.
- **Core formulas** live once in `packages/domain-py` and are consumed by `apps/api` and `apps/worker`.

## Technology stack

| Layer        | Choice |
|--------------|--------|
| Monorepo     | Turborepo, pnpm (JS), pip + venv (Python), Makefile |
| Frontend     | Next.js (App Router), TypeScript strict, Tailwind, shadcn/ui, Lucide, MapLibre GL, deck.gl, TanStack Query/Table, ECharts, RHF + Zod |
| Backend      | FastAPI, Pydantic, SQLAlchemy 2.0 async, GeoAlchemy2, Alembic, orjson, httpx |
| ML           | scikit-learn, CatBoost, LightGBM, Isolation Forest, SHAP, Parquet |
| Database     | PostgreSQL 15+ with PostGIS + pgcrypto (SRID 4326 / WGS 84) |
| Jobs         | APScheduler (deterministic default); ARQ when Redis enabled |
| Infra/CI     | Docker Compose, GitHub Actions |

## Repository structure

```
apps/        web, api, worker, ml-lab, docs
packages/    ui, maps, charts, contracts, api-client, domain, config,
             testing, eslint-config, typescript-config, domain-py
data/        raw, processed, fixtures, synthetic
infra/       docker, migrations, deployment
scripts/     contract generation, migrate, seed, demo reset
docs/        architecture, adr, api, data, demo
```

## Prerequisites

- Node.js (active LTS; see `.nvmrc`) and **pnpm 10+**
- Python **3.11+** and **pip**
- Docker + Docker Compose (for PostgreSQL/PostGIS)

## Local setup

```bash
cp .env.example .env
pnpm install
./scripts/pip-install.sh
docker compose up -d postgres      # waits for PostGIS to be healthy
pnpm db:migrate
pnpm db:seed
pnpm dev
```

For MOMENT TSFM scoring, install ML extras then enable in `.env`:

```bash
./scripts/pip-install.sh              # base worker (fast)
./scripts/pip-install-ml.sh           # MOMENT deps only (~2GB download)
# set MOMENT_ENABLED=true in .env
source .venv/bin/activate
python -m gridtrace_worker.main score-moment
```

Or the shortcut:

```bash
make install && make up && make migrate && make seed && make dev
```

| Service | URL |
|---------|-----|
| Web     | http://localhost:3000 |
| API     | http://localhost:8003 |
| OpenAPI | http://localhost:8003/docs |

> **Note:** Local development uses port **8003** for the API (instead of 8000) to avoid
> conflicts with other services — especially Docker containers that commonly bind to 8000.

**Offline demo mode:** set `NEXT_PUBLIC_DEMO_MODE=true` and the web app serves
itself from in-browser mocks + cached GeoJSON — no backend or database required.

## Environment variables

See [`.env.example`](./.env.example). Public browser values are prefixed
`NEXT_PUBLIC_`; everything else is server-side only. Secrets are never committed,
and local filesystem storage is used when object storage is not configured.

## Database migrations

```bash
pnpm db:migrate                         # alembic upgrade head
source .venv/bin/activate
cd apps/api && python -m alembic revision --autogenerate -m "change"
```

Seed data is kept **out** of migrations. See [`apps/api/alembic/README.md`](./apps/api/alembic/README.md).

## Synthetic data

Deterministic, seeded by `DEMO_SEED`. The worker generates 1 operator, 5
neighborhoods, 10 transformers, ~1000 customers, and 60 days of hourly readings,
plus 3 seeded incidents (partial bypass, coordinated cluster, meter fault). See
[`docs/data/synthetic-data.md`](./docs/data/synthetic-data.md).

## Running tests

```bash
pnpm test          # TS unit (Vitest)
pnpm test:e2e      # Playwright primary flow
source .venv/bin/activate
pytest             # Python unit + integration
```

## Demo workflow

```bash
pnpm demo:reset    # deterministic clear → regenerate → score → verify
```

Then follow [`docs/demo/demo-script.md`](./docs/demo/demo-script.md):
Command Center → Risk Map hotspot → Transformer Digital Twin → reconciliation →
suspicious customer → score/evidence/peers → add to inspection mission → record outcome.

## Deployment

- **Web** → Vercel (or any Next.js host)
- **API** → container (`infra/docker/api.Dockerfile`)
- **Worker** → separate process from the same image family
- **Database** → managed PostgreSQL with PostGIS
- Migrations run as an explicit release step.

## Ethical limitations

See [`docs/architecture/ethics.md`](./docs/architecture/ethics.md). In short:
non-accusatory language, synthetic data only, visible confidence and alternative
explanations, and mandatory human inspection before any action.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md).
