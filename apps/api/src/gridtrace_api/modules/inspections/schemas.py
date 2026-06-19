from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InspectionQueueItem(BaseModel):
    customer_id: str
    external_ref: str
    risk_score: float
    risk_tier: str
    inspection_priority: float
    estimated_loss_kwh: float
    estimated_loss_value: float
    currency: str
    recommended_action: str
    region_name: str | None


class InspectionMissionOut(BaseModel):
    id: str
    name: str
    region_id: str | None
    status: str
    scheduled_date: datetime | None
    assigned_team_id: str | None
    route_geometry: dict[str, Any] | None
    estimated_total_value: float
    currency: str
    created_by: str
    created_at: datetime
    case_count: int


class InspectionCaseOut(BaseModel):
    id: str
    mission_id: str
    customer_id: str
    risk_score_id: str | None
    status: str
    priority_rank: int
    scheduled_at: datetime | None
    assigned_to: str | None
    recommended_action: str | None
    notes: str | None


class InspectionOutcomeOut(BaseModel):
    id: str
    inspection_case_id: str
    outcome: str
    confirmed_loss_type: str | None
    estimated_recovered_kwh: float | None
    estimated_recovered_value: float | None
    evidence: dict[str, Any]
    submitted_by: str
    submitted_at: datetime


class CreateMissionRequest(BaseModel):
    name: str
    region_id: str | None = None
    scheduled_date: datetime | None = None
    assigned_team_id: str | None = None


class CreateCaseRequest(BaseModel):
    customer_id: str
    risk_score_id: str | None = None
    recommended_action: str | None = None
    notes: str | None = None


class UpdateCaseRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    scheduled_at: datetime | None = None
    notes: str | None = None


class SubmitOutcomeRequest(BaseModel):
    outcome: str
    confirmed_loss_type: str | None = None
    estimated_recovered_kwh: float | None = None
    estimated_recovered_value: float | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class RouteRequest(BaseModel):
    customer_ids: list[str]


class RouteResponse(BaseModel):
    ordered_customer_ids: list[str]
    route_geometry: dict[str, Any]
    total_distance_km: float
