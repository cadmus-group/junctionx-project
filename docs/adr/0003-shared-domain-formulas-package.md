# ADR-0003: Shared Python domain formulas package

- Status: Accepted
- Date: 2026-06-19

## Context

The core formulas (unexplained loss, risk score, attribution, inspection priority)
are consumed by both `apps/api` and `apps/worker`. The spec forbids duplicating
domain formulas or schemas.

## Decision

Add a lightweight, dependency-free uv workspace member `packages/domain-py`
(import `gridtrace_domain`) as the single source of truth. `apps/api` and
`apps/worker` depend on it via `[tool.uv.sources] gridtrace-domain = { workspace = true }`.
This extends the originally listed workspace members (api, worker, ml-lab) — a
deliberate, documented deviation to satisfy the no-duplication constraint.

## Consequences

- Formulas are tested once and reused everywhere; weights are versioned.
- `apps/api` stays free of heavy ML dependencies.
