from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RiskTierCount(BaseModel):
    tier: str
    count: int


class DashboardSummary(BaseModel):
    total_customers: int
    total_transformers: int
    total_unexplained_loss_kwh: float
    total_estimated_loss_value: float
    currency: str
    period_start: datetime
    period_end: datetime
    high_risk_count: int
    critical_risk_count: int
    open_inspections: int
    risk_tier_breakdown: list[RiskTierCount]
    model_version: str
    feature_version: str


class LossTrendPoint(BaseModel):
    timestamp: datetime
    energy_input_kwh: float
    metered_output_kwh: float
    technical_loss_kwh: float
    unexplained_loss_kwh: float


class LossTrend(BaseModel):
    unit: str = "kWh"
    points: list[LossTrendPoint]
