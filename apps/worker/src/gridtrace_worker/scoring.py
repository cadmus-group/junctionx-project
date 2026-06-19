"""Pure, deterministic feature -> risk-component mapping.

No request-time training: the supervised component is a transparent, deterministic
logistic heuristic over theft-indicative features. (A heavier model can be trained
in ``apps/ml-lab`` and its metrics recorded in the model registry; the worker stays
fully deterministic so the demo is reproducible.)

Each component is clamped to [0, 1]; the composite 0-100 score and tier come from
``gridtrace_domain`` so the worker never re-implements the weighting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gridtrace_domain import (
    RiskComponents,
    risk_score,
    risk_tier_for_score,
)

# Normalization references (documented calibration constants).
GRID_RATIO_REF = 0.12
PEER_DEV_REF = 0.70
SPATIAL_REF = 0.50
ANOMALY_Z_K = 3.0
SUPERVISED_SLOPE = 2.0
FLATLINE_SUPERVISED_DAMPING = 0.70  # meter-fault flatline suppresses theft confidence

# Transformer-level mapping references.
TX_SUPERVISED_LO = 0.02
TX_SUPERVISED_SPAN = 0.06
TX_PEER_DROP_REF = 0.20


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass(frozen=True)
class ScoredEntity:
    components: RiskComponents
    score: float
    tier: str
    confidence: float
    suspicion_weight: float


def customer_components(features: dict) -> ScoredEntity:
    drop_severity = _clamp01(1.0 - features.get("drop_ratio", 1.0))
    peer_dev = features.get("peer_deviation", 0.0)
    flatline = float(features.get("flatline", 0.0))
    anomaly_z = abs(features.get("anomaly_z", 0.0))

    inner = SUPERVISED_SLOPE * (2.2 * drop_severity + 1.8 * max(0.0, peer_dev) - 0.55)
    supervised = _sigmoid(inner)
    supervised *= 1.0 - FLATLINE_SUPERVISED_DAMPING * flatline

    anomaly = 1.0 - math.exp(-anomaly_z / ANOMALY_Z_K)
    anomaly = max(anomaly, flatline)  # a flatline is a strong anomaly

    grid = _clamp01(features.get("grid_unexplained_ratio", 0.0) / GRID_RATIO_REF)
    peer = _clamp01(max(0.0, peer_dev) / PEER_DEV_REF)
    spatial = _clamp01(features.get("spatial_neighborhood_risk", 0.0) / SPATIAL_REF)

    components = RiskComponents(
        supervised_probability=_clamp01(supervised),
        anomaly_score=_clamp01(anomaly),
        grid_imbalance_score=grid,
        peer_score=peer,
        spatial_score=spatial,
    )
    score = risk_score(components)
    tier = risk_tier_for_score(score)
    # Confidence is reduced for flatline (likely meter fault, not theft).
    confidence = _clamp01(0.45 + 0.5 * supervised - 0.35 * flatline)
    suspicion_weight = max(1e-6, components.supervised_probability)
    return ScoredEntity(components, score, tier, confidence, suspicion_weight)


def transformer_components(features: dict) -> ScoredEntity:
    ratio = features.get("unexplained_ratio", 0.0)
    frac_drop = features.get("frac_members_dropping", 0.0)
    member_anomaly_z = features.get("max_member_anomaly_z", 0.0)

    supervised = _clamp01((ratio - TX_SUPERVISED_LO) / TX_SUPERVISED_SPAN)
    anomaly = max(
        _clamp01(ratio / GRID_RATIO_REF),
        1.0 - math.exp(-abs(member_anomaly_z) / ANOMALY_Z_K),
    )
    grid = _clamp01(ratio / GRID_RATIO_REF)
    peer = _clamp01(frac_drop / TX_PEER_DROP_REF)
    spatial = _clamp01(features.get("mean_peer_deviation", 0.0) / SPATIAL_REF)

    components = RiskComponents(
        supervised_probability=supervised,
        anomaly_score=_clamp01(anomaly),
        grid_imbalance_score=grid,
        peer_score=peer,
        spatial_score=spatial,
    )
    score = risk_score(components)
    tier = risk_tier_for_score(score)
    confidence = _clamp01(0.5 + 0.4 * supervised)
    suspicion_weight = max(1e-6, supervised)
    return ScoredEntity(components, score, tier, confidence, suspicion_weight)


_COMPONENT_LABELS = {
    "supervised_probability": ("Theft-pattern likelihood", "Supervised model probability of non-technical loss."),
    "anomaly_score": ("Consumption anomaly", "Unsupervised deviation of recent consumption from its own baseline."),
    "grid_imbalance_score": ("Grid energy imbalance", "Unexplained-loss ratio on the parent transformer."),
    "peer_score": ("Peer deviation", "How far below comparable peers the recent consumption sits."),
    "spatial_score": ("Neighborhood risk", "Aggregate risk of the surrounding neighborhood."),
}


def build_explanations(
    entity: ScoredEntity,
    features: dict,
    loss_attribution_share: float,
) -> list[dict]:
    """Top contributing components + the loss-attribution share entry.

    The API reads the ``loss_attribution_share`` entry's ``contribution`` directly,
    so it is always included as a [0, 1] value.
    """
    comp = entity.components
    items = []
    for key in (
        "supervised_probability",
        "anomaly_score",
        "grid_imbalance_score",
        "peer_score",
        "spatial_score",
    ):
        value = getattr(comp, key)
        label, detail = _COMPONENT_LABELS[key]
        items.append(
            {
                "feature": key,
                "label": label,
                "contribution": round(float(value), 4),
                "direction": "increases" if value >= 0.5 else "neutral",
                "detail": detail,
            }
        )
    items.sort(key=lambda e: e["contribution"], reverse=True)
    top = items[:4]

    if features.get("flatline", 0.0) >= 1.0:
        top.append(
            {
                "feature": "flatline",
                "label": "Flatlined meter",
                "contribution": 1.0,
                "direction": "increases",
                "detail": "Meter reads near-zero with no variation; investigate meter fault before fraud escalation.",
            }
        )

    top.append(
        {
            "feature": "loss_attribution_share",
            "label": "Share of transformer unexplained loss",
            "contribution": round(float(loss_attribution_share), 6),
            "direction": "increases" if loss_attribution_share > 0 else "neutral",
            "detail": "Operational estimate of this entity's share of the parent transformer's unexplained loss.",
        }
    )
    return top
