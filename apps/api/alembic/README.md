# Alembic migrations

The initial migration creates the PostGIS/pgcrypto extensions and builds the full
schema from the SQLAlchemy metadata so the database can be constructed from an empty
state. Subsequent schema changes should be added as incremental, reversible revisions:

```bash
cd apps/api
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Seed data is kept out of migrations (see `scripts/db-seed.sh` and `apps/worker`).
