from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gridtrace_api.db.base import Base, uuid_pk


class GridAsset(Base):
    __tablename__ = "grid_assets"
    __table_args__ = (
        Index("ix_grid_assets_geometry", "geometry", postgresql_using="gist"),
        Index("ix_grid_assets_operator_type", "operator_id", "asset_type"),
    )

    id: Mapped[str] = uuid_pk()
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), nullable=False)
    parent_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("grid_assets.id"), nullable=True
    )
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    voltage_level: Mapped[str | None] = mapped_column(String, nullable=True)
    capacity_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_geometry", "geometry", postgresql_using="gist"),
        Index("ix_customers_transformer_id", "transformer_id"),
    )

    id: Mapped[str] = uuid_pk()
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String, nullable=False)
    meter_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("grid_assets.id"), nullable=True
    )
    transformer_id: Mapped[str | None] = mapped_column(
        ForeignKey("grid_assets.id"), nullable=True
    )
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("grid_assets.id"), nullable=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    customer_type: Mapped[str] = mapped_column(String, nullable=False)
    tariff_type: Mapped[str | None] = mapped_column(String, nullable=True)
    building_type: Mapped[str | None] = mapped_column(String, nullable=True)
    woningwaarde_category: Mapped[str | None] = mapped_column(String, nullable=True)
    solar_potential_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (Index("ix_meter_readings_meter_ts", "meter_id", "timestamp"),)

    id: Mapped[str] = uuid_pk()
    meter_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    current: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_quality: Mapped[str] = mapped_column(String, default="good")
    source: Mapped[str] = mapped_column(String, default="ami")


class AssetEnergyReading(Base):
    __tablename__ = "asset_energy_readings"
    __table_args__ = (Index("ix_asset_energy_readings_asset_ts", "asset_id", "timestamp"),)

    id: Mapped[str] = uuid_pk()
    asset_id: Mapped[str] = mapped_column(ForeignKey("grid_assets.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_input_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    energy_output_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_quality: Mapped[str] = mapped_column(String, default="good")
    source: Mapped[str] = mapped_column(String, default="scada")


class TechnicalLossEstimate(Base):
    __tablename__ = "technical_loss_estimates"
    __table_args__ = (
        Index("ix_technical_loss_estimates_asset_ts", "asset_id", "timestamp"),
    )

    id: Mapped[str] = uuid_pk()
    asset_id: Mapped[str] = mapped_column(ForeignKey("grid_assets.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_technical_loss_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String, default="loss_factor")
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    model_version: Mapped[str] = mapped_column(String, default="tech-loss-v1")
