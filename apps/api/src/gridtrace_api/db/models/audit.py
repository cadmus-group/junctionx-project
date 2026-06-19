from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gridtrace_api.db.base import Base, created_at_column, uuid_pk


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    actor: Mapped[str] = mapped_column(String, default="system")
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at_column()
