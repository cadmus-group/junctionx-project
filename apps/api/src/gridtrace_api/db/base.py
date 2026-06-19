"""SQLAlchemy declarative base and shared column types."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk():
    return mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_column():
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
