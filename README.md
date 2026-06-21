# Atlas

> Find where energy disappears, explain why, and prioritize what to inspect.

Atlas detects **probable non-technical electricity losses** (theft, meter
tampering, faults) using consumption analytics, machine learning, grid energy
reconciliation, GIS clustering, explainability, and inspection prioritization.

This is a **hackathon MVP**: a Turborepo monorepo with a modular-monolith FastAPI
backend, a background worker, an ML lab, and a Next.js operator console. It runs
fully offline with deterministic synthetic data.

> ⚠️ **Ethics:** Atlas produces *operational signals to prioritize inspection*,
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

**One command (Windows, macOS, Linux):**

```bash
cp .env.example .env
pnpm install
pnpm setup          # sync Python deps, start Postgres, migrate, seed scores
pnpm dev            # web + API together
```

Or step by step:

```bash
pnpm py:sync        # uv sync Python 3.11 (api + worker)
pnpm db:up          # docker compose up -d postgres
pnpm db:migrate
pnpm db:seed        # synthetic grid + meter readings + risk_scores
pnpm dev
```

**Load data via CSV** (same scoring pipeline, different entry path):

```bash
pnpm db:ingest-production   # auto-exports demo CSVs if missing, then ingest + score
```

Set `NEXT_PUBLIC_DEMO_MODE=false` in `.env` so the frontend reads live API data (not MSW mocks).

For MOMENT TSFM scoring, install ML extras then enable in `.env`:

```bash
pnpm py:sync:ml     # optional MOMENT deps (~2GB download)
# set MOMENT_ENABLED=true in .env
uv run --python 3.11 --package gridtrace-worker python -m gridtrace_worker.main score-moment
```

Offline GBM experiments (research only — not wired to live API scoring):

```bash
pnpm py:sync:ml
pnpm ml:train
```

Or the Makefile shortcut (requires Git Bash on Windows):

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

### User roles (demo login)

The console has three role-based views — the "Përdoruesit Kryesorë" from the brief.
On the login screen **any password with 8+ characters** works; the **username selects
the role**:

| Username | Role | View |
|----------|------|------|
| `operator`  | **Distribution Operator** | Oversight: Command Center KPIs, Risk Map, Inspections (+ Settings) |
| `analyst`   | **Analyst Team** | Triage: Customers, Assets, Model Analytics, Data Quality, Inspections |
| `inspector` | **Field Inspector** | Field work: Risk Map + assigned Inspections |

Every role shares the same shell (top bar, main content, the map); only the sidebar
navigation differs.

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

## Data, privacy & ethics

GridTrace is built for a **public energy operator**, so it is designed to be
privacy-respecting and non-accusatory by default. See
[`docs/architecture/ethics.md`](./docs/architecture/ethics.md). In short:

- **Metering points, not people.** The system scores **metering points /
  connections**, identified only by a pseudonymous meter reference (e.g.
  `NL-MTR-00012`). It stores consumption and grid features — **no names, no
  addresses, no personal identity**. Data minimization by design.
- **Signals, not accusations.** Outputs are *risk indicators to prioritize
  inspection* — never determinations of wrongdoing. The UI uses non-accusatory
  language and always shows confidence and alternative explanations (e.g. meter
  faults, estimation gaps, occupancy changes).
- **Human in the loop.** A confirmed result always requires an **on-site human
  inspection**; no action is taken from a score alone.
- **Synthetic data only.** All data in this repo is deterministic synthetic data
  — no real customers are involved.
- **Role-scoped access.** Operator / analyst / inspector each see only what their
  role needs.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md).
