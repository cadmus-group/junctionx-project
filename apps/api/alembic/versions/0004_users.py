"""Login users table

Revision ID: 0004_users
Revises: 0003_dutch_energy_context
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_users"
down_revision: str | None = "0003_dutch_energy_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR NOT NULL,
            username VARCHAR(50) NOT NULL,
            name VARCHAR NOT NULL,
            role VARCHAR NOT NULL,
            password_hash VARCHAR NOT NULL,
            operator_id VARCHAR,
            CONSTRAINT pk_users PRIMARY KEY (id),
            CONSTRAINT uq_users_username UNIQUE (username),
            CONSTRAINT fk_users_operator_id_operators
                FOREIGN KEY (operator_id) REFERENCES operators (id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("DROP TABLE IF EXISTS users")
