"""Unique indexes for idempotent production CSV ingest

Revision ID: 0005_production_ingest_indexes
Revises: 0004_add_users_table
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_production_ingest_indexes"
down_revision: str | None = "0004_add_users_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_customers_operator_external_ref",
        "customers",
        ["operator_id", "external_ref"],
        unique=True,
    )
    op.create_index(
        "uq_grid_assets_operator_external_id",
        "grid_assets",
        ["operator_id", "external_id"],
        unique=True,
    )
    op.create_index(
        "uq_meter_readings_meter_ts",
        "meter_readings",
        ["meter_id", "timestamp"],
        unique=True,
    )
    op.create_index(
        "uq_asset_energy_readings_asset_ts",
        "asset_energy_readings",
        ["asset_id", "timestamp"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_asset_energy_readings_asset_ts", table_name="asset_energy_readings")
    op.drop_index("uq_meter_readings_meter_ts", table_name="meter_readings")
    op.drop_index("uq_grid_assets_operator_external_id", table_name="grid_assets")
    op.drop_index("uq_customers_operator_external_ref", table_name="customers")
