"""initial schema with PostGIS

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from gridtrace_api.db.base import Base

# Import models so all tables are registered on the metadata.
import gridtrace_api.db.models  # noqa: F401

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
