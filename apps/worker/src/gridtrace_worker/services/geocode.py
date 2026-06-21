"""PDOK Locatieserver geocoding for Dutch postcodes and streets.

PDOK (https://www.pdok.nl) exposes a free, key-less REST geocoder. We use it to
turn Stedin postcodes/streets into real WGS84 coordinates instead of synthetic
hash positions. Results are cached on disk so repeated ingests do not re-hit the
service, and any failure (offline, timeout, no match) falls back to the caller's
approximation - mirroring the offline-fallback pattern used by the NED connector.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

from gridtrace_worker.log import get_logger, log_event

logger = get_logger("geocode")

# Current PDOK Locatieserver "free" search endpoint (Solr-backed).
PDOK_BASE_URL = os.getenv(
    "PDOK_LOCATIESERVER_URL",
    "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free",
)
PDOK_TIMEOUT = float(os.getenv("PDOK_TIMEOUT", "10"))
# Parallelism for the prewarm pass (PDOK tolerates modest concurrency).
PDOK_WORKERS = int(os.getenv("PDOK_WORKERS", "12"))
# Master switch; set STEDIN_GEOCODE=false to skip live geocoding entirely.
GEOCODE_ENABLED = os.getenv("STEDIN_GEOCODE", "true").strip().lower() not in {"0", "false", "no", "off"}
# After this many failures with zero successes we assume PDOK is unreachable and
# stop hammering it for the remainder of the run.
_FAILURE_CIRCUIT = 5

_POINT_RE = re.compile(r"POINT\(\s*([-0-9.]+)\s+([-0-9.]+)\s*\)")


def _parse_point(value: str | None) -> tuple[float, float] | None:
    """Parse a PDOK ``centroide_ll`` WKT string ``POINT(lon lat)``."""
    if not value:
        return None
    match = _POINT_RE.search(value)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


class PdokGeocoder:
    """Cached geocoder backed by the PDOK Locatieserver free endpoint."""

    def __init__(
        self,
        cache_path: Path | str | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        self.enabled = GEOCODE_ENABLED if enabled is None else enabled
        self.cache_path = Path(cache_path) if cache_path else None
        self._cache: dict[str, list[float] | None] = {}
        self._dirty = False
        self._client: httpx.Client | None = None
        self.hits = 0
        self.misses = 0
        self.failures = 0
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path and self.cache_path.is_file():
            try:
                data = json.loads(self.cache_path.read_text())
                if isinstance(data, dict):
                    self._cache = data
            except (OSError, ValueError):
                self._cache = {}

    def save(self) -> None:
        if self.cache_path and self._dirty:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache))
            self._dirty = False

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=PDOK_TIMEOUT)
        return self._client

    def close(self) -> None:
        self.save()
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "PdokGeocoder":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def lookup(self, postcode: str, street: str = "", city: str = "") -> tuple[float, float] | None:
        """Return ``(lon, lat)`` for the best PDOK match, or ``None`` if unavailable.

        Cache key is the normalised full postcode, which in the Netherlands is
        precise to a single street segment.
        """
        key = postcode.replace(" ", "").upper()
        if not key:
            return None
        if key in self._cache:
            cached = self._cache[key]
            return (cached[0], cached[1]) if cached else None
        if not self.enabled:
            return None

        result = self._query(key, street, city)
        self._cache[key] = list(result) if result else None
        self._dirty = True
        if result:
            self.hits += 1
        else:
            self.misses += 1
        return result

    def prewarm(self, items: Iterable[tuple[str, str, str]], max_workers: int = PDOK_WORKERS) -> None:
        """Populate the cache for many ``(postcode, street, city)`` keys in parallel.

        This keeps a full ingest to a couple of minutes instead of ~1.5s per
        sequential lookup. Subsequent ``lookup`` calls are pure cache reads.
        """
        if not self.enabled:
            return
        pending: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for postcode, street, city in items:
            key = postcode.replace(" ", "").upper()
            if not key or key in self._cache or key in seen:
                continue
            seen.add(key)
            pending.append((key, street, city))
        if not pending:
            return

        workers = max(1, min(max_workers, len(pending)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._query, key, street, city): key for key, street, city in pending
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    point = future.result()
                except Exception:  # defensive: never let one key abort the batch
                    point = None
                self._cache[key] = list(point) if point else None
                self._dirty = True
                if point:
                    self.hits += 1
                else:
                    self.misses += 1
        self.save()

    def _query(self, postcode: str, street: str, city: str) -> tuple[float, float] | None:
        # 1) Exact full postcode - street-precise in the Netherlands.
        if len(postcode) >= 6:
            point = self._search(postcode, "type:postcode")
            if point:
                return point
        # 2) Street within the city (also covers synthetic pc4 anchors).
        terms = " ".join(part for part in (street, city) if part).strip()
        if terms:
            point = self._search(terms, "type:weg")
            if point:
                return point
        # 3) 4-digit postcode area as a last resort before the caller's fallback.
        pc4 = postcode[:4]
        if pc4.isdigit():
            return self._search(pc4, "type:postcode")
        return None

    def _search(self, q: str, fq: str) -> tuple[float, float] | None:
        if not self.enabled:
            return None
        try:
            resp = self.client.get(
                PDOK_BASE_URL,
                params={"q": q, "fq": fq, "rows": 1, "fl": "centroide_ll", "wt": "json"},
            )
            resp.raise_for_status()
            docs = resp.json().get("response", {}).get("docs", [])
        except Exception as exc:  # network/parse errors -> caller fallback
            self.failures += 1
            if self.failures <= 3:
                log_event(logger, "pdok_geocode_error", q=q, error=str(exc))
            if self.failures >= _FAILURE_CIRCUIT and self.hits == 0:
                self.enabled = False
                log_event(logger, "pdok_geocode_disabled", failures=self.failures)
            return None
        if not docs:
            return None
        return _parse_point(docs[0].get("centroide_ll"))
