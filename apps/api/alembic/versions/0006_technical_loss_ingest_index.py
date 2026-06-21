"""Unique index for idempotent technical loss CSV ingest

Revision ID: 0006_technical_loss_ingest_index
Revises: 0005_production_ingest_indexes
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_technical_loss_ingest_index"
down_revision: str | None = "0005_production_ingest_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_technical_loss_estimates_asset_ts",
        "technical_loss_estimates",
        ["asset_id", "timestamp"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_technical_loss_estimates_asset_ts", table_name="technical_loss_estimates")
