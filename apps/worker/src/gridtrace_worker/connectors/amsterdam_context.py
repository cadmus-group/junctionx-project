"""Amsterdam open-data context connectors (offline fixtures).

Maps customer coordinates to Woningwaarde tiers and Zonatlas solar-potential flags
using deterministic nearest-zone lookups from local JSON fixtures.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gridtrace_worker.connectors.base import ConnectorResult, OfflineConnector


@dataclass(frozen=True)
class Zone:
    lon: float
    lat: float
    radius_deg: float
    payload: dict[str, Any]


class AmsterdamContextConnector(OfflineConnector):
    name = "amsterdam_context"

    def __init__(self, fixtures_root: Path | str | None = None) -> None:
        root = Path(fixtures_root) if fixtures_root else _default_fixtures_root()
        self.woningwaarde = _load_zones(root / "amsterdam_woningwaarde.json", "category")
        self.zonatlas = _load_zones(root / "amsterdam_zonatlas.json", "label")

    def fetch(self) -> ConnectorResult:
        records = [
            {
                "source": "woningwaarde",
                "zones": [z.payload for z in self.woningwaarde],
            },
            {
                "source": "zonatlas",
                "zones": [z.payload for z in self.zonatlas],
            },
        ]
        return ConnectorResult(records=records, freshness=self._freshness(records))

    def classify_customer(self, lon: float, lat: float) -> dict[str, Any]:
        category = _nearest_zone(lon, lat, self.woningwaarde)
        solar_zone = _nearest_zone(lon, lat, self.zonatlas)
        solar_flag = solar_zone is not None and _within_zone(lon, lat, solar_zone)
        return {
            "woningwaarde_category": category.payload.get("category") if category else None,
            "solar_potential_flag": bool(solar_flag),
            "zonatlas_label": solar_zone.payload.get("label") if solar_zone else None,
        }


def _default_fixtures_root() -> Path:
    return Path(__file__).resolve().parents[5] / "data" / "fixtures"


def _load_zones(path: Path, label_key: str) -> list[Zone]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text())
    zones: list[Zone] = []
    for item in raw:
        zones.append(
            Zone(
                lon=float(item["lon"]),
                lat=float(item["lat"]),
                radius_deg=float(item.get("radius_deg", 0.01)),
                payload={label_key: item[label_key], **item},
            )
        )
    return zones


def _within_zone(lon: float, lat: float, zone: Zone) -> bool:
    return _distance_deg(lon, lat, zone.lon, zone.lat) <= zone.radius_deg


def _nearest_zone(lon: float, lat: float, zones: list[Zone]) -> Zone | None:
    if not zones:
        return None
    return min(zones, key=lambda z: _distance_deg(lon, lat, z.lon, z.lat))


def _distance_deg(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    return math.hypot(lon1 - lon2, lat1 - lat2)
