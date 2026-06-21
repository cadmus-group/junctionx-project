"""Ensure the demo login user exists (required for API auth after production ingest)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from gridtrace_api.db.models.user import User
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_NAME,
    DEMO_OPERATOR_PASSWORD_HASH,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)


def ensure_demo_user(session: Session) -> User:
    """Upsert demo_operator so login works after non-synthetic data loads."""
    existing = session.execute(
        select(User).where(User.username == DEMO_OPERATOR_USERNAME)
    ).scalar_one_or_none()

    if existing:
        existing.full_name = DEMO_OPERATOR_NAME
        existing.role = DEMO_OPERATOR_ROLE
        existing.hashed_password = DEMO_OPERATOR_PASSWORD_HASH
        existing.is_active = True
        return existing

    user = User(
        id=DEMO_OPERATOR_ID,
        username=DEMO_OPERATOR_USERNAME,
        full_name=DEMO_OPERATOR_NAME,
        role=DEMO_OPERATOR_ROLE,
        hashed_password=DEMO_OPERATOR_PASSWORD_HASH,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user
