"""Helpers for converting between PostGIS geometries and GeoJSON."""

from __future__ import annotations

import json
from typing import Any

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping


def geometry_to_geojson(geom: Any) -> dict[str, Any] | None:
    """Convert a GeoAlchemy2 geometry element to a GeoJSON geometry dict."""
    if geom is None:
        return None
    try:
        shape = to_shape(geom)
        return mapping(shape)
    except Exception:
        return None


def feature(geometry: dict[str, Any] | None, properties: dict[str, Any], fid: Any = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties,
    }
    if fid is not None:
        out["id"] = fid
    return out


def feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def point_geojson(lon: float, lat: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def parse_geojson(value: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return value
