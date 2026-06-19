from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gridtrace_api.db.base import Base, created_at_column, uuid_pk


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        Index("ix_feature_snapshots_entity", "entity_type", "entity_id", "as_of"),
    )

    id: Mapped[str] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    feature_version: Mapped[str] = mapped_column(String, nullable=False)


class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("ix_risk_scores_entity", "entity_type", "entity_id", "scored_at"),
        Index("ix_risk_scores_ranking", "risk_score", "inspection_priority"),
    )

    id: Mapped[str] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False)
    supervised_probability: Mapped[float] = mapped_column(Float, default=0.0)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    grid_imbalance_score: Mapped[float] = mapped_column(Float, default=0.0)
    peer_score: Mapped[float] = mapped_column(Float, default=0.0)
    spatial_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_loss_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_loss_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    inspection_priority: Mapped[float] = mapped_column(Float, default=0.0)
    explanations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    feature_version: Mapped[str] = mapped_column(String, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_score_id: Mapped[str | None] = mapped_column(
        ForeignKey("risk_scores.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = created_at_column()


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = uuid_pk()
    model_version: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    feature_version: Mapped[str] = mapped_column(String, nullable=False)
    algorithm: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    k: Mapped[int] = mapped_column(Integer, default=100)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
