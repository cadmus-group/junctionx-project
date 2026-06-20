from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gridtrace_api.modules.risk.schemas import RiskScoreOut


class CustomerOut(BaseModel):
    id: str
    operator_id: str
    external_ref: str
    transformer_id: str | None
    feeder_id: str | None
    region_id: str | None
    customer_type: str
    tariff_type: str | None
    building_type: str | None
    baseline_annual_kwh: float | None = None
    street_smartmeter_perc: float | None = None
    geometry: dict[str, Any] | None
    risk_score: float | None
    risk_tier: str | None


class MeterReadingOut(BaseModel):
    timestamp: datetime
    consumption_kwh: float
    voltage: float | None
    current: float | None
    power_factor: float | None
    reading_quality: str
    source: str


class CustomerReadings(BaseModel):
    customer_id: str
    unit: str = "kWh"
    readings: list[MeterReadingOut]


class PeerComparisonPoint(BaseModel):
    timestamp: datetime
    customer_kwh: float
    peer_median_kwh: float
    expected_kwh: float


class SpatialContextOut(BaseModel):
    baseline_annual_kwh: float | None = None
    street_smartmeter_perc: float | None = None
    recent_annualized_kwh: float | None = None
    baseline_deviation_ratio: float | None = None


class CustomerRiskProfile(BaseModel):
    customer: CustomerOut
    risk: RiskScoreOut
    peer_comparison: list[PeerComparisonPoint]
    spatial_context: SpatialContextOut | None = None
    loss_attribution_share: float
    notes: list[str]
