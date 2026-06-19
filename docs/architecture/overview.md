# Architecture overview

GridTrace is a **Turborepo monorepo** with a **modular-monolith** FastAPI backend
and a **separate background worker** process. No microservices, no Kubernetes.

## Workspaces

- **JavaScript/TypeScript** via pnpm workspaces (`apps/web`, `apps/docs`, `packages/*`).
- **Python** via uv workspace (`apps/api`, `apps/worker`, `apps/ml-lab`, `packages/domain-py`).
- **Turborepo** orchestrates JS tasks; Python tasks are invoked through root scripts
  and the Makefile (see [ADR-0002](../adr/0002-turborepo-python-integration.md)).

## Backend module pattern

Each feature module under `apps/api/src/gridtrace_api/modules/<feature>/` has:

- `router.py` — transport validation only
- `schemas.py` — Pydantic request/response models
- `service.py` — business logic
- `repository.py` — persistence queries
- `exceptions.py` (when needed)

Rules: routers never contain business logic; services never expose SQLAlchemy models;
responses use Pydantic models; errors are RFC 7807 problem details; timestamps are
UTC ISO 8601; units are explicit; risk responses carry `model_version` + `feature_version`.

## Contract flow (one direction only)

```
FastAPI app.openapi()  →  packages/contracts/openapi.json
                       →  packages/contracts/generated/*.ts (openapi-typescript)
                       →  packages/api-client (typed client + TanStack Query options)
                       →  apps/web
```

Contracts are **generated**, never hand-duplicated. CI fails if they are stale.

## Shared domain formulas

`packages/domain-py` (`gridtrace_domain`) holds the authoritative formulas. Both
`apps/api` and `apps/worker` import them so numbers never diverge. See
[risk-formula.md](./risk-formula.md).

## Data layer

PostgreSQL 15+ with PostGIS (SRID 4326) and pgcrypto. Async SQLAlchemy 2.0 +
GeoAlchemy2. Alembic builds the schema from an empty database; seed data is kept
out of migrations.
