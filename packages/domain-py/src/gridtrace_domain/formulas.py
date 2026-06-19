"""Core GridTrace domain formulas.

Do not change weights, thresholds, or formula structure without updating the
configuration version, tests, docs, and demo fixtures (see coordination_rules).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

EPSILON = 1e-09

RISK_WEIGHTS_VERSION = "risk-weights-v1"


@dataclass(frozen=True)
class RiskWeights:
    """Weights for the composite risk score. Each input score is in [0, 1]."""

    supervised_probability: float = 0.40
    anomaly_score: float = 0.25
    grid_imbalance_score: float = 0.20
    peer_score: float = 0.10
    spatial_score: float = 0.05

    def total(self) -> float:
        return (
            self.supervised_probability
            + self.anomaly_score
            + self.grid_imbalance_score
            + self.peer_score
            + self.spatial_score
        )


DEFAULT_RISK_WEIGHTS = RiskWeights()


@dataclass(frozen=True)
class RiskComponents:
    """Component scores, each expected in [0, 1]."""

    supervised_probability: float
    anomaly_score: float
    grid_imbalance_score: float
    peer_score: float
    spatial_score: float


# (label, min, max) inclusive bounds on the 0-100 score.
RISK_TIERS: tuple[tuple[str, int, int], ...] = (
    ("LOW", 0, 29),
    ("WATCH", 30, 49),
    ("MEDIUM", 50, 69),
    ("HIGH", 70, 84),
    ("CRITICAL", 85, 100),
)


def unexplained_loss(
    energy_in_kwh: float,
    metered_consumption_kwh: Iterable[float] | float,
    estimated_technical_loss_kwh: float,
) -> float:
    """UnexplainedLoss = EnergyIn - sum(MeteredConsumption) - EstimatedTechnicalLoss.

    The signed residual is preserved for diagnostics; a negative result is a valid
    signal (e.g. metering over-reporting or input under-measurement). Clamp only in
    presentation or prioritization, never here.
    """
    if isinstance(metered_consumption_kwh, (int, float)):
        metered_total = float(metered_consumption_kwh)
    else:
        metered_total = float(sum(metered_consumption_kwh))
    return float(energy_in_kwh) - metered_total - float(estimated_technical_loss_kwh)


def unexplained_loss_ratio(unexplained_loss_kwh: float, energy_in_kwh: float) -> float:
    """UnexplainedLossRatio = UnexplainedLoss / max(EnergyIn, epsilon)."""
    return float(unexplained_loss_kwh) / max(float(energy_in_kwh), EPSILON)


def _validate_unit_interval(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return float(value)


def risk_score(
    components: RiskComponents,
    weights: RiskWeights = DEFAULT_RISK_WEIGHTS,
) -> float:
    """Composite risk score in [0, 100].

    RiskScore = 100 * (0.40*P_supervised + 0.25*S_anomaly + 0.20*S_grid
                       + 0.10*S_peer + 0.05*S_spatial)
    """
    p = _validate_unit_interval("supervised_probability", components.supervised_probability)
    a = _validate_unit_interval("anomaly_score", components.anomaly_score)
    g = _validate_unit_interval("grid_imbalance_score", components.grid_imbalance_score)
    pe = _validate_unit_interval("peer_score", components.peer_score)
    s = _validate_unit_interval("spatial_score", components.spatial_score)

    weighted = (
        weights.supervised_probability * p
        + weights.anomaly_score * a
        + weights.grid_imbalance_score * g
        + weights.peer_score * pe
        + weights.spatial_score * s
    )
    return round(100.0 * weighted, 4)


def risk_tier_for_score(score: float) -> str:
    """Map a 0-100 score to its tier label."""
    clamped = max(0.0, min(100.0, float(score)))
    for label, low, high in RISK_TIERS:
        if low <= clamped <= high:
            return label
    return "CRITICAL"


def customer_loss_attribution(
    suspicion_weight: float,
    all_suspicion_weights: Iterable[float],
    transformer_unexplained_loss_kwh: float,
) -> float:
    """Attribution_c = w_c / sum(w_j) * UnexplainedLoss_transformer.

    Operational estimate only; never present as legal proof.
    """
    total_weight = float(sum(all_suspicion_weights))
    if total_weight <= EPSILON:
        return 0.0
    share = float(suspicion_weight) / total_weight
    return share * float(transformer_unexplained_loss_kwh)


def estimated_loss_value(estimated_loss_kwh: float, applicable_energy_price: float) -> float:
    """EstimatedLossValue = EstimatedLossKWh * ApplicableEnergyPrice (in currency units)."""
    return float(estimated_loss_kwh) * float(applicable_energy_price)


def inspection_priority(
    p_ntl: float,
    estimated_recoverable_value: float,
    confidence: float,
    expected_inspection_cost: float,
    optional_factor: float = 1.0,
) -> float:
    """InspectionPriority = P(NTL) * RecoverableValue * Confidence - ExpectedCost.

    Returns the raw priority value (currency-scaled). `optional_factor` folds in
    optional multiplicative adjustments (travel time, cluster efficiency, asset
    criticality, case age) when provided.
    """
    return (
        float(p_ntl)
        * float(estimated_recoverable_value)
        * float(confidence)
        * float(optional_factor)
    ) - float(expected_inspection_cost)


def normalize_priority(
    raw_priority: float,
    raw_priorities: Iterable[float] | Mapping[str, float],
) -> float:
    """Normalize a raw priority into a 0-100 display score via min-max scaling."""
    values = (
        list(raw_priorities.values())
        if isinstance(raw_priorities, Mapping)
        else list(raw_priorities)
    )
    if not values:
        return 0.0
    lo = min(values)
    hi = max(values)
    if hi - lo <= EPSILON:
        return 50.0
    return round(100.0 * (float(raw_priority) - lo) / (hi - lo), 2)
