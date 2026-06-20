"""Nationaal Energie Dashboard (NED) connector.

Polls https://api.ned.nl/v1 for national load and production mix. When no API key
is configured, returns deterministic offline fixtures so the demo remains reproducible.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from gridtrace_worker.connectors.base import ConnectorResult, OfflineConnector

NED_BASE_URL = "https://api.ned.nl/v1"
NED_UTILIZATIONS = f"{NED_BASE_URL}/utilizations"


class NEDConnector(OfflineConnector):
    """Fetch macro grid baseline rows for DuckDB ``ned_grid_status.parquet``."""

    name = "ned"

    def __init__(self, api_key: str | None = None, fixture_path: Path | str | None = None) -> None:
        self.api_key = api_key
        if fixture_path is None:
            fixture_path = (
                Path(__file__).resolve().parents[5] / "data" / "fixtures" / "ned_grid_status.json"
            )
        self.fixture_path = Path(fixture_path)

    def fetch(self, hours: int = 48) -> ConnectorResult:
        if self.api_key:
            try:
                records = self._fetch_live(hours)
                return ConnectorResult(
                    records=records,
                    freshness=self._freshness(records, mode="live"),
                )
            except Exception as exc:  # pragma: no cover - network failures fall back
                offline = self._fetch_offline(hours)
                return ConnectorResult(
                    records=offline,
                    freshness=self._freshness(
                        offline,
                        mode="offline_fallback",
                        error=str(exc),
                    ),
                )
        records = self._fetch_offline(hours)
        return ConnectorResult(
            records=records,
            freshness=self._freshness(records, mode="offline"),
        )

    def _fetch_live(self, hours: int) -> list[dict[str, Any]]:
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        start = now - timedelta(hours=hours)
        headers = {"X-AUTH-TOKEN": self.api_key or "", "accept": "application/ld+json"}
        params = {
            "point": 0,
            "type": 2,
            "granularity": 3,
            "granularitytimezone": 1,
            "classification": 2,
            "activity": 1,
            "validfrom[after]": start.strftime("%Y-%m-%d"),
            "validfrom[strictly_before]": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
        with httpx.Client(timeout=30.0) as client:
            load_resp = client.get(NED_UTILIZATIONS, headers=headers, params=params)
            load_resp.raise_for_status()
            load_rows = _parse_utilizations(load_resp.json())

            solar_params = {**params, "classification": 1, "point": 1}
            wind_params = {**params, "classification": 1, "point": 2}
            solar_resp = client.get(NED_UTILIZATIONS, headers=headers, params=solar_params)
            wind_resp = client.get(NED_UTILIZATIONS, headers=headers, params=wind_params)
            solar_rows = _parse_utilizations(solar_resp.json()) if solar_resp.is_success else {}
            wind_rows = _parse_utilizations(wind_resp.json()) if wind_resp.is_success else {}

        records: list[dict[str, Any]] = []
        for ts, load_mw in sorted(load_rows.items()):
            solar = float(solar_rows.get(ts, 0.0))
            wind = float(wind_rows.get(ts, 0.0))
            total_gen = max(solar + wind, 1.0)
            records.append(
                {
                    "timestamp": ts,
                    "national_load_mw": round(load_mw, 4),
                    "production_mix_solar": round(solar / total_gen, 6),
                    "production_mix_wind": round(wind / total_gen, 6),
                    "grid_status_flag": _grid_status(load_mw, solar, wind),
                }
            )
        return records[-hours:] if records else self._fetch_offline(hours)

    def _fetch_offline(self, hours: int) -> list[dict[str, Any]]:
        if self.fixture_path.is_file():
            raw = json.loads(self.fixture_path.read_text())
            return raw[-hours:]

        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        records: list[dict[str, Any]] = []
        for h in range(hours):
            ts = (now - timedelta(hours=hours - 1 - h)).isoformat()
            hour = (now - timedelta(hours=hours - 1 - h)).hour
            load = 9500.0 + 800.0 * ((hour - 12) / 12.0)
            solar_share = max(0.0, 0.35 * (1.0 - abs(hour - 13) / 13.0))
            wind_share = 0.25
            total = max(solar_share + wind_share, 0.01)
            records.append(
                {
                    "timestamp": ts,
                    "national_load_mw": round(load, 4),
                    "production_mix_solar": round(solar_share / total, 6),
                    "production_mix_wind": round(wind_share / total, 6),
                    "grid_status_flag": "normal",
                }
            )
        return records


def _parse_utilizations(payload: Any) -> dict[str, float]:
    """Extract timestamp -> MW from NED hydra/ld+json payloads."""
    items: list[Any]
    if isinstance(payload, dict):
        if "hydra:member" in payload:
            items = payload["hydra:member"]
        elif "member" in payload:
            items = payload["member"]
        else:
            items = payload.get("@graph", [])
    elif isinstance(payload, list):
        items = payload
    else:
        return {}

    out: dict[str, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        ts = item.get("validfrom") or item.get("validFrom") or item.get("timestamp")
        value = item.get("value") or item.get("volume") or item.get("amount")
        if ts is None or value is None:
            continue
        try:
            out[str(ts)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _grid_status(load_mw: float, solar: float, wind: float) -> str:
    if load_mw > 12000:
        return "high_demand"
    if solar + wind < 500:
        return "low_renewables"
    return "normal"
