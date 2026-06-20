"""Amsterdam context columns on customers

Revision ID: 0002_amsterdam_context
Revises: 0001_initial
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_amsterdam_context"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("woningwaarde_category", sa.String(), nullable=True))
    op.add_column(
        "customers",
        sa.Column("solar_potential_flag", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("customers", "solar_potential_flag", server_default=None)


def downgrade() -> None:
    op.drop_column("customers", "solar_potential_flag")
    op.drop_column("customers", "woningwaarde_category")
