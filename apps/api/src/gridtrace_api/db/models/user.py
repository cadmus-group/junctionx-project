from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from gridtrace_api.db.base import Base, uuid_pk


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[str] = uuid_pk()
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("operators.id"), nullable=True
    )
