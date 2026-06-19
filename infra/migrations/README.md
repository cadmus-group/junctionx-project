# Migrations

Database migrations are managed by **Alembic** and live with the API app at
[`apps/api/alembic`](../../apps/api/alembic). Apply them with:

```bash
pnpm db:migrate     # or: make migrate
```

This directory is reserved for cross-service infrastructure migration notes and
release runbooks (e.g. enabling PostGIS on a managed instance).
