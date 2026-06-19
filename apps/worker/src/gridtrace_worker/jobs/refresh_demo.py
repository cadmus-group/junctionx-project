"""Demo refresh helpers: safe truncation of operational data and verification.

``truncate_operational`` clears only the operational/demo tables (never migrations
or schema). ``verify`` asserts the seeded showcase invariants: the partial-bypass
customer is CRITICAL and the showcase transformer's energy balance reconciles with a
plausible unexplained-loss ratio.
"""

from __future__ import annotations

from gridtrace_api.db.models import Customer, FeatureSnapshot, RiskScore
from gridtrace_domain import unexplained_loss, unexplained_loss_ratio
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event

logger = get_logger("refresh_demo")

# Operational tables only (NOT alembic_version / schema). CASCADE handles FK order.
_OPERATIONAL_TABLES = [
    "audit_logs",
    "inspection_outcomes",
    "inspection_cases",
    "inspection_missions",
    "alerts",
    "risk_scores",
    "feature_snapshots",
    "model_registry",
    "technical_loss_estimates",
    "asset_energy_readings",
    "meter_readings",
    "customers",
    "grid_assets",
    "regions",
    "operators",
]

RATIO_BAND = (0.085, 0.115)
RECONCILE_TOLERANCE_KWH = 1.0


def truncate_operational(session: Session) -> None:
    tables = ", ".join(_OPERATIONAL_TABLES)
    session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    log_event(logger, "operational_data_truncated", tables=len(_OPERATIONAL_TABLES))


def verify(session: Session) -> tuple[bool, dict]:
    checks: dict[str, object] = {}
    ok = True

    # 1) Partial-bypass showcase customer must be CRITICAL.
    customers = session.execute(
        select(Customer.id, Customer.external_ref, Customer.transformer_id, Customer.metadata_json)
    ).all()
    bypass = next(
        (c for c in customers if (c.metadata_json or {}).get("incident") == "partial_bypass"),
        None,
    )
    if bypass is None:
        return False, {"error": "partial_bypass customer not found"}

    risk = session.execute(
        select(RiskScore).where(
            RiskScore.entity_type == "customer",
            RiskScore.entity_id == bypass.id,
            RiskScore.is_current.is_(True),
        )
    ).scalar_one_or_none()
    critical_ok = bool(risk and risk.risk_tier == "CRITICAL")
    ok = ok and critical_ok
    checks["showcase_customer"] = {
        "external_ref": bypass.external_ref,
        "risk_score": round(risk.risk_score, 2) if risk else None,
        "risk_tier": risk.risk_tier if risk else None,
        "expected_tier": "CRITICAL",
        "passed": critical_ok,
    }

    # 2) Showcase transformer reconciliation + plausible ratio.
    tx_id = bypass.transformer_id
    tx_snap = session.execute(
        select(FeatureSnapshot).where(
            FeatureSnapshot.entity_type == "transformer",
            FeatureSnapshot.entity_id == tx_id,
        )
    ).scalar_one_or_none()
    if tx_snap is None:
        return False, {**checks, "error": "showcase transformer snapshot not found"}

    f = tx_snap.features_json
    input_total = float(f.get("input_total_kwh", 0.0))
    metered_total = float(f.get("metered_total_kwh", 0.0))
    technical_total = float(f.get("technical_total_kwh", 0.0))
    stored_unexplained = float(f.get("unexplained_total_kwh", 0.0))
    recomputed = unexplained_loss(input_total, metered_total, technical_total)
    ratio = unexplained_loss_ratio(recomputed, input_total)
    reconcile_ok = abs(recomputed - stored_unexplained) <= RECONCILE_TOLERANCE_KWH
    ratio_ok = RATIO_BAND[0] <= ratio <= RATIO_BAND[1]
    ok = ok and reconcile_ok and ratio_ok
    checks["showcase_transformer"] = {
        "energy_input_kwh": round(input_total, 2),
        "metered_kwh": round(metered_total, 2),
        "technical_kwh": round(technical_total, 2),
        "unexplained_kwh": round(recomputed, 2),
        "unexplained_ratio": round(ratio, 4),
        "ratio_band": list(RATIO_BAND),
        "reconciles": reconcile_ok,
        "ratio_in_band": ratio_ok,
    }

    log_event(logger, "demo_verified", passed=ok, checks=checks)
    return ok, checks
