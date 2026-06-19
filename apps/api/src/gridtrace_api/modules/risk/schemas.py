from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from gridtrace_api.db.models import RiskScore


class RiskComponents(BaseModel):
    supervised_probability: float
    anomaly_score: float
    grid_imbalance_score: float
    peer_score: float
    spatial_score: float


class RiskExplanation(BaseModel):
    feature: str
    label: str
    contribution: float
    direction: str
    detail: str | None = None


class RiskScoreOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    scored_at: datetime
    risk_score: float
    risk_tier: str
    components: RiskComponents
    confidence: float
    estimated_loss_kwh: float
    estimated_loss_value: float
    currency: str
    inspection_priority: float
    explanations: list[RiskExplanation]
    model_version: str
    feature_version: str

    @classmethod
    def from_model(cls, m: RiskScore) -> RiskScoreOut:
        return cls(
            id=m.id,
            entity_type=m.entity_type,
            entity_id=m.entity_id,
            scored_at=m.scored_at,
            risk_score=m.risk_score,
            risk_tier=m.risk_tier,
            components=RiskComponents(
                supervised_probability=m.supervised_probability,
                anomaly_score=m.anomaly_score,
                grid_imbalance_score=m.grid_imbalance_score,
                peer_score=m.peer_score,
                spatial_score=m.spatial_score,
            ),
            confidence=m.confidence,
            estimated_loss_kwh=m.estimated_loss_kwh,
            estimated_loss_value=m.estimated_loss_value,
            currency=m.currency,
            inspection_priority=m.inspection_priority,
            explanations=[RiskExplanation(**e) for e in (m.explanations_json or [])],
            model_version=m.model_version,
            feature_version=m.feature_version,
        )
