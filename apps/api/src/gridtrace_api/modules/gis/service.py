from __future__ import annotations

from collections import defaultdict
from typing import Any

from geoalchemy2.functions import ST_MakeEnvelope
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import Customer, RiskScore
from gridtrace_api.shared.geo import feature, feature_collection, geometry_to_geojson


async def anomalies_geojson(
    session: AsyncSession,
    bbox: tuple[float, float, float, float] | None,
    min_risk: float = 0.0,
) -> dict[str, Any]:
    """Customer-level risk points as a GeoJSON FeatureCollection."""
    stmt = (
        select(Customer, RiskScore)
        .join(
            RiskScore,
            (RiskScore.entity_id == Customer.id)
            & (RiskScore.entity_type == "customer")
            & (RiskScore.is_current.is_(True)),
        )
        .where(RiskScore.risk_score >= min_risk)
    )
    if bbox is not None:
        envelope = ST_MakeEnvelope(bbox[0], bbox[1], bbox[2], bbox[3], 4326)
        stmt = stmt.where(func.ST_Intersects(Customer.geometry, envelope))

    rows = (await session.execute(stmt)).all()
    features = []
    for customer, risk in rows:
        geom = geometry_to_geojson(customer.geometry)
        if geom is None:
            continue
        features.append(
            feature(
                geom,
                {
                    "customer_id": customer.id,
                    "external_ref": customer.external_ref,
                    "risk_score": risk.risk_score,
                    "risk_tier": risk.risk_tier,
                    "estimated_loss_kwh": risk.estimated_loss_kwh,
                    "transformer_id": customer.transformer_id,
                },
                fid=customer.id,
            )
        )
    return feature_collection(features)


async def hotspots(
    session: AsyncSession, resolution: int = 3, min_risk: float = 0.0
) -> dict[str, Any]:
    """Coarse grid aggregation of customer risk into polygon hotspot cells.

    `resolution` controls cell size in decimal degrees (higher = finer). This is a
    lightweight stand-in for an H3 heatmap that keeps the demo dependency-free.
    """
    cell = 1.0 / (2 ** max(1, min(resolution, 7)))
    stmt = (
        select(
            func.ST_X(Customer.geometry).label("lon"),
            func.ST_Y(Customer.geometry).label("lat"),
            RiskScore.risk_score,
            RiskScore.estimated_loss_kwh,
        )
        .join(
            RiskScore,
            (RiskScore.entity_id == Customer.id)
            & (RiskScore.entity_type == "customer")
            & (RiskScore.is_current.is_(True)),
        )
        .where(RiskScore.risk_score >= min_risk, Customer.geometry.isnot(None))
    )
    rows = (await session.execute(stmt)).all()

    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    losses: dict[tuple[int, int], float] = defaultdict(float)
    for lon, lat, score, loss in rows:
        key = (int(lon // cell), int(lat // cell))
        buckets[key].append(float(score))
        losses[key] += float(loss or 0.0)

    features = []
    for (gx, gy), scores in buckets.items():
        min_lon = gx * cell
        min_lat = gy * cell
        max_lon = min_lon + cell
        max_lat = min_lat + cell
        mean_risk = sum(scores) / len(scores)
        polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]
            ],
        }
        features.append(
            feature(
                polygon,
                {
                    "mean_risk": round(mean_risk, 2),
                    "max_risk": round(max(scores), 2),
                    "customer_count": len(scores),
                    "estimated_loss_kwh": round(losses[(gx, gy)], 2),
                },
            )
        )
    return feature_collection(features)
