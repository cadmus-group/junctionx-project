"""Dutch energy spatial context columns on customers

Revision ID: 0003_dutch_energy_context
Revises: 0002_amsterdam_context
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_dutch_energy_context"
down_revision: str | None = "0002_amsterdam_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS zipcode VARCHAR")
    op.execute(
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS baseline_annual_kwh NUMERIC"
    )
    op.execute(
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS street_smartmeter_perc NUMERIC"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_customers_zipcode ON customers (zipcode)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_customers_zipcode")
    op.drop_column("customers", "street_smartmeter_perc")
    op.drop_column("customers", "baseline_annual_kwh")
    op.drop_column("customers", "zipcode")
