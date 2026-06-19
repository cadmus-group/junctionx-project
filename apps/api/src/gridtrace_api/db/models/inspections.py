from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gridtrace_api.db.base import Base, created_at_column, uuid_pk


class InspectionMission(Base):
    __tablename__ = "inspection_missions"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_team_id: Mapped[str | None] = mapped_column(String, nullable=True)
    route_geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )
    estimated_total_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    created_by: Mapped[str] = mapped_column(String, default="system")
    created_at: Mapped[datetime] = created_at_column()


class InspectionCase(Base):
    __tablename__ = "inspection_cases"

    id: Mapped[str] = uuid_pk()
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("inspection_missions.id"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    risk_score_id: Mapped[str | None] = mapped_column(
        ForeignKey("risk_scores.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default="queued")
    priority_rank: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class InspectionOutcome(Base):
    __tablename__ = "inspection_outcomes"

    id: Mapped[str] = uuid_pk()
    inspection_case_id: Mapped[str] = mapped_column(
        ForeignKey("inspection_cases.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    confirmed_loss_type: Mapped[str | None] = mapped_column(String, nullable=True)
    estimated_recovered_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_recovered_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    submitted_by: Mapped[str] = mapped_column(String, default="inspector")
    submitted_at: Mapped[datetime] = created_at_column()
