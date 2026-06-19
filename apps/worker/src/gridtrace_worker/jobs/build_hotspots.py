"""Hotspot aggregation job.

Aggregates the current customer risk scores into per-region (neighborhood) hotspot
summaries and records the result into ``audit_logs``. The API serves live GeoJSON
hotspots directly from customer points; this job provides a precomputed,
auditable neighborhood roll-up (mean/max risk, customer count, estimated loss).

Idempotent: a prior hotspot audit record for the same as-of is replaced.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from gridtrace_api.db.models import AuditLog, Customer, RiskScore
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event

logger = get_logger("build_hotspots")

_ACTION = "build_hotspots"


def run(session: Session, seed: int | None = None) -> dict:
    rows = session.execute(
        select(
            Customer.region_id,
            RiskScore.risk_score,
            RiskScore.estimated_loss_kwh,
            RiskScore.estimated_loss_value,
        ).join(
            RiskScore,
            (RiskScore.entity_id == Customer.id)
            & (RiskScore.entity_type == "customer")
            & (RiskScore.is_current.is_(True)),
        )
    ).all()

    scores: dict[str, list[float]] = defaultdict(list)
    loss_kwh: dict[str, float] = defaultdict(float)
    loss_value: dict[str, float] = defaultdict(float)
    for region_id, score, lkwh, lval in rows:
        key = region_id or "unassigned"
        scores[key].append(float(score))
        loss_kwh[key] += float(lkwh or 0.0)
        loss_value[key] += float(lval or 0.0)

    hotspots = []
    for region_id, vals in scores.items():
        hotspots.append(
            {
                "region_id": region_id,
                "customer_count": len(vals),
                "mean_risk": round(sum(vals) / len(vals), 2),
                "max_risk": round(max(vals), 2),
                "estimated_loss_kwh": round(loss_kwh[region_id], 2),
                "estimated_loss_value": round(loss_value[region_id], 2),
            }
        )
    hotspots.sort(key=lambda h: h["mean_risk"], reverse=True)

    session.execute(delete(AuditLog).where(AuditLog.action == _ACTION))
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action=_ACTION,
            entity_type="region_hotspots",
            entity_id=None,
            payload_json={
                "built_at": datetime.now(UTC).isoformat(),
                "hotspots": hotspots,
            },
        )
    )

    log_event(logger, "hotspots_built", regions=len(hotspots))
    return {"regions": len(hotspots), "hotspots": hotspots}
