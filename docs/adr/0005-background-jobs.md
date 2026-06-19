# ADR-0005: APScheduler default, ARQ when Redis is enabled

- Status: Accepted
- Date: 2026-06-19

## Context

The demo must run deterministically and offline, without requiring Redis.

## Decision

The worker uses **APScheduler** as the deterministic default for scheduled jobs and
runs pipeline commands directly via its CLI. When `REDIS_URL` is set, **ARQ** can be
used for distributed queuing. Redis is **optional** (`redis` Docker Compose profile).

## Consequences

- Zero external broker required for the hackathon demo.
- A clear upgrade path to a real queue exists when Redis is provisioned.
