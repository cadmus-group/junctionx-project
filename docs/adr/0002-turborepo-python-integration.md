# ADR-0002: Turborepo / Python task integration

- Status: Accepted
- Date: 2026-06-19

## Context

Turborepo orchestrates tasks across the **pnpm** workspace, but the Python apps
(`apps/api`, `apps/worker`, `apps/ml-lab`) live in a **uv** workspace that Turbo does
not manage directly.

## Decision

Python tasks are invoked through **root npm scripts and the Makefile**, which shell out
to `uv` (e.g. `pnpm db:migrate` → `scripts/db-migrate.sh` → `uv run alembic ...`). The
contract-generation task bridges both worlds: it exports the FastAPI OpenAPI schema via
`uv`, then runs `openapi-typescript` via `pnpm`.

We deliberately did **not** add fake `package.json` shims for each Python app to avoid
polluting the pnpm graph. CI runs the JS and Python jobs separately.

## Consequences

- Single, documented entry points (`pnpm`, `make`, `uv`).
- Python builds are not cached by Turbo; acceptable for the MVP.
