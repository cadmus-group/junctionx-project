# ADR-0004: One-way generated API contracts

- Status: Accepted
- Date: 2026-06-19

## Context

Frontend/backend contracts must never be hand-duplicated, and drift must be caught
automatically.

## Decision

The **FastAPI OpenAPI schema is the source of truth**. `pnpm generate:contracts`
exports it to `packages/contracts/openapi.json` and generates TypeScript types into
`packages/contracts/generated/` via `openapi-typescript`. `packages/api-client`
wraps those types into a typed HTTP client and TanStack Query options consumed by
`apps/web`. The hand-stable primitives in `packages/contracts/src` (GeoJSON,
pagination, problem details, DTO shapes) mirror the backend and are kept in lockstep.

CI regenerates contracts and **fails when the git diff is non-empty**.

## Consequences

- No manual contract duplication; drift is a CI failure.
- Generated files are never hand-edited.
