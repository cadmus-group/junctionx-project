from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GridAssetOut(BaseModel):
    id: str
    operator_id: str
    parent_asset_id: str | None
    asset_type: str
    external_id: str
    name: str
    voltage_level: str | None
    capacity_kva: float | None
    geometry: dict[str, Any] | None
    region_id: str | None
    risk_tier: str | None
    risk_score: float | None


class WaterfallStep(BaseModel):
    label: str
    value: float
    kind: str  # input | deduction | residual


class TransformerReconciliation(BaseModel):
    transformer_id: str
    name: str
    period_start: datetime
    period_end: datetime
    energy_input_kwh: float
    metered_output_kwh: float
    estimated_technical_loss_kwh: float
    unexplained_loss_kwh: float
    unexplained_loss_ratio: float
    customer_count: int
    risk_tier: str
    risk_score: float
    waterfall: list[WaterfallStep]
    currency: str
    estimated_loss_value: float


class AssetCustomerSummary(BaseModel):
    customer_id: str
    external_ref: str
    customer_type: str
    risk_score: float | None
    risk_tier: str | None
    estimated_loss_kwh: float | None
