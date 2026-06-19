from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from gridtrace_api.dependencies import CurrentUserDep, SessionDep
from gridtrace_api.modules.gis import service

router = APIRouter(prefix="/gis", tags=["gis"])


@router.get("/anomalies/geojson")
async def anomalies_geojson(
    session: SessionDep,
    _user: CurrentUserDep,
    min_lon: float | None = None,
    min_lat: float | None = None,
    max_lon: float | None = None,
    max_lat: float | None = None,
    min_risk: float = 0.0,
) -> dict[str, Any]:
    bbox: tuple[float, float, float, float] | None = None
    if (
        min_lon is not None
        and min_lat is not None
        and max_lon is not None
        and max_lat is not None
    ):
        bbox = (min_lon, min_lat, max_lon, max_lat)
    return await service.anomalies_geojson(session, bbox, min_risk)


@router.get("/hotspots")
async def hotspots(
    session: SessionDep,
    _user: CurrentUserDep,
    resolution: int = 3,
    min_risk: float = 0.0,
) -> dict[str, Any]:
    return await service.hotspots(session, resolution, min_risk)
