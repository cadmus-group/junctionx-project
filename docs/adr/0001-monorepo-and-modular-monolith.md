# ADR-0001: Turborepo monorepo with a modular-monolith backend

- Status: Accepted
- Date: 2026-06-19

## Context

GridTrace must be runnable, typed, GIS-capable, and demoable within a hackathon while
remaining production-extensible. The team is small and the demo must run offline.

## Decision

Use a single **Turborepo monorepo** containing TypeScript (pnpm) and Python (uv)
workspaces. The backend is a **modular monolith** (FastAPI with feature modules) plus
a **separate worker process** for heavy jobs. No microservices, no Kubernetes.

## Consequences

- One repo, one task graph, atomic cross-cutting changes.
- Clear module boundaries (`router/service/repository/schemas`) ease later extraction.
- The worker isolates ingestion/scoring from request latency.
