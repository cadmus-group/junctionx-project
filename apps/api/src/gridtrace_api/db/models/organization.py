from __future__ import annotations

from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gridtrace_api.db.base import Base, uuid_pk


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="UTC")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    regions: Mapped[list[Region]] = relationship(back_populates="operator")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = uuid_pk()
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"), nullable=False)
    parent_region_id: Mapped[str | None] = mapped_column(
        ForeignKey("regions.id"), nullable=True
    )
    region_type: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True
    )
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    operator: Mapped[Operator] = relationship(back_populates="regions")
