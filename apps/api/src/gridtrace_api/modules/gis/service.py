from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import Customer, RiskScore
from gridtrace_api.shared.geo import feature, feature_collection

_HIGH_RISK_METERS_SQL = """
SELECT jsonb_build_object(
    'type', 'FeatureCollection',
    'features', COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'id', c.id,
                'geometry', ST_AsGeoJSON(c.geometry)::jsonb,
                'properties', jsonb_build_object(
                    'customer_id', c.id,
                    'external_ref', c.external_ref,
                    'risk_score', rs.risk_score,
                    'risk_tier', rs.risk_tier,
                    'estimated_loss_kwh', rs.estimated_loss_kwh,
                    'transformer_id', c.transformer_id,
                    'baseline_annual_kwh', c.baseline_annual_kwh,
                    'street_smartmeter_perc', c.street_smartmeter_perc
                )
            )
            ORDER BY rs.risk_score DESC
        ) FILTER (WHERE c.id IS NOT NULL),
        '[]'::jsonb
    )
) AS geojson
FROM customers c
INNER JOIN risk_scores rs
    ON rs.entity_id = c.id
   AND rs.entity_type = 'customer'
   AND rs.is_current IS TRUE
WHERE rs.risk_score >= :min_risk
  AND c.geometry IS NOT NULL
  {bbox_clause}
"""


async def get_high_risk_meters(
    session: AsyncSession,
    bbox: tuple[float, float, float, float] | None,
    min_risk: float = 0.0,
) -> dict[str, Any]:
    """Customer-level risk points as GeoJSON via PostGIS native aggregation."""
    params: dict[str, Any] = {"min_risk": min_risk}
    if bbox is not None:
        params.update(
            {
                "min_lon": bbox[0],
                "min_lat": bbox[1],
                "max_lon": bbox[2],
                "max_lat": bbox[3],
            }
        )
        bbox_clause = (
            "AND ST_Intersects("
            "c.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            ")"
        )
    else:
        bbox_clause = ""

    stmt = text(_HIGH_RISK_METERS_SQL.format(bbox_clause=bbox_clause))
    result = await session.execute(stmt, params)
    geojson = result.scalar_one()
    return geojson if isinstance(geojson, dict) else dict(geojson)


async def anomalies_geojson(
    session: AsyncSession,
    bbox: tuple[float, float, float, float] | None,
    min_risk: float = 0.0,
) -> dict[str, Any]:
    """Customer-level risk points as a GeoJSON FeatureCollection."""
    return await get_high_risk_meters(session, bbox, min_risk)


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
