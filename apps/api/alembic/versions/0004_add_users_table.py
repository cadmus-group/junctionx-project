"""Add users table and seed demo login user

Revision ID: 0004_add_users_table
Revises: 0003_dutch_energy_context
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_users_table"
down_revision: str | None = "0003_dutch_energy_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# bcrypt hash for password "SuperSecret123!" (rounds=12)
_DEMO_OPERATOR_HASH = (
    "$2b$12$uJVI9cBy.BaJVjpkZx6LU.ZWrZC.PYiec4tkK2eB7yjnPb8tl2DRO"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, username, full_name, hashed_password, role, is_active, created_at)
            VALUES (
                'user-12345',
                'demo_operator',
                'Demo Operator',
                :hashed_password,
                'operator',
                true,
                NOW()
            )
            ON CONFLICT (username) DO NOTHING
            """
        ).bindparams(hashed_password=_DEMO_OPERATOR_HASH)
    )


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
