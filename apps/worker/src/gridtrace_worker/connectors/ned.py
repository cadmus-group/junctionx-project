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

# NED enum identifiers (see /v1/points, /v1/types, /v1/classifications, /v1/activities,
# /v1/granularities). ``point`` is the geographic region and ``type`` the energy carrier.
NED_POINT_NL = 0  # Nederland (national)
NED_TYPE_WIND = 1
NED_TYPE_SOLAR = 2
NED_TYPE_ELECTRICITY_MIX = 27
NED_CLASSIFICATION_CURRENT = 2
NED_ACTIVITY_PROVIDING = 1
NED_GRANULARITY_HOUR = 5


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
        # Baseline series: national electricity mix (total supplied power). Solar and
        # wind use the same query with a different energy ``type`` for the mix shares.
        params = {
            "point": NED_POINT_NL,
            "type": NED_TYPE_ELECTRICITY_MIX,
            "granularity": NED_GRANULARITY_HOUR,
            "granularitytimezone": 1,
            "classification": NED_CLASSIFICATION_CURRENT,
            "activity": NED_ACTIVITY_PROVIDING,
            "validfrom[after]": start.strftime("%Y-%m-%d"),
            "validfrom[strictly_before]": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
        with httpx.Client(timeout=30.0) as client:
            load_resp = client.get(NED_UTILIZATIONS, headers=headers, params=params)
            load_resp.raise_for_status()
            load_rows = _parse_utilizations(load_resp.json())

            solar_params = {**params, "type": NED_TYPE_SOLAR}
            wind_params = {**params, "type": NED_TYPE_WIND}
            solar_resp = client.get(NED_UTILIZATIONS, headers=headers, params=solar_params)
            wind_resp = client.get(NED_UTILIZATIONS, headers=headers, params=wind_params)
            solar_rows = _parse_utilizations(solar_resp.json()) if solar_resp.is_success else {}
            wind_rows = _parse_utilizations(wind_resp.json()) if wind_resp.is_success else {}

        # NED reports energy volume (kWh) per sub-hourly slice. _parse_utilizations
        # sums those slices into hourly buckets; hourly kWh over a 1-hour window is
        # numerically the average power in kW, so divide by 1000 to get MW.
        records: list[dict[str, Any]] = []
        for ts, load_kwh in sorted(load_rows.items()):
            load_mw = load_kwh / 1000.0
            solar_mw = float(solar_rows.get(ts, 0.0)) / 1000.0
            wind_mw = float(wind_rows.get(ts, 0.0)) / 1000.0
            total_gen = max(solar_mw + wind_mw, 1.0)
            records.append(
                {
                    "timestamp": ts,
                    "national_load_mw": round(load_mw, 4),
                    "production_mix_solar": round(solar_mw / total_gen, 6),
                    "production_mix_wind": round(wind_mw / total_gen, 6),
                    "grid_status_flag": _grid_status(load_mw, solar_mw, wind_mw),
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


def _hour_bucket(ts: str) -> str:
    """Truncate an ISO-8601 timestamp to the start of its hour."""
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return parsed.replace(minute=0, second=0, microsecond=0).isoformat()


def _parse_utilizations(payload: Any) -> dict[str, float]:
    """Extract hourly timestamp -> summed energy volume (kWh) from NED payloads.

    NED returns sub-hourly slices (e.g. 10-minute ``volume`` in kWh). Slices are
    summed into hourly buckets so callers can derive an average MW load.
    """
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
        value = item.get("volume")
        if value is None:
            value = item.get("value") or item.get("amount")
        if ts is None or value is None:
            continue
        try:
            hour_key = _hour_bucket(str(ts))
            out[hour_key] = out.get(hour_key, 0.0) + float(value)
        except (TypeError, ValueError):
            continue
    return out


def _grid_status(load_mw: float, solar: float, wind: float) -> str:
    if load_mw > 12000:
        return "high_demand"
    if solar + wind < 500:
        return "low_renewables"
    return "normal"
