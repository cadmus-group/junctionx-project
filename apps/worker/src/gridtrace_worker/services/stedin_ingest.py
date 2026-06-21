"""Transform Stedin kleinverbruikgegevens CSVs into production ingest files.

Stedin publishes tab-separated street-segment statistics (ELK = electricity).
We expand annual SJA (kWh) into hourly profiles so the existing feature/scoring
pipeline can run unchanged.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import PRODUCTION_SUBDIR

logger = get_logger("stedin_ingest")

STEDIN_SUBDIR = "Stedin"
STEDIN_GLOB = "Stedin kleinverbruikgegevens *.csv"
OPERATOR_NAME = "Stedin"

MAX_SEGMENTS = int(os.getenv("STEDIN_MAX_SEGMENTS", "2000"))
PROFILE_HOURS = int(os.getenv("STEDIN_PROFILE_HOURS", "1440"))

# Approximate WGS84 centroids by Dutch postcode area (PC2 = first two digits).
_NL_PC2_CENTROIDS: dict[int, tuple[float, float]] = {
    10: (4.89, 52.37),
    11: (4.94, 52.30),
    12: (5.17, 52.22),
    13: (5.26, 52.35),
    14: (4.95, 52.51),
    15: (4.83, 52.44),
    24: (4.30, 52.07),
    25: (4.29, 52.08),
    26: (4.30, 52.04),
    27: (4.49, 52.02),
    28: (4.65, 52.01),
    29: (4.53, 51.85),
    30: (4.48, 51.92),
    31: (4.39, 51.91),
    32: (4.33, 51.85),
    33: (4.67, 51.81),
    34: (4.65, 51.82),
    35: (4.69, 51.83),
    36: (4.75, 51.82),
    37: (4.78, 51.81),
    38: (4.82, 51.82),
    39: (4.85, 51.83),
    40: (4.90, 51.82),
    41: (4.95, 51.83),
    42: (5.00, 51.84),
    43: (5.05, 51.85),
    44: (5.10, 51.86),
    45: (5.15, 51.87),
    46: (5.20, 51.88),
    47: (5.25, 51.89),
    48: (5.30, 51.90),
    49: (5.35, 51.91),
    50: (5.40, 51.92),
    51: (5.45, 51.93),
    52: (5.50, 51.94),
    53: (5.55, 51.95),
    54: (5.60, 51.96),
    55: (5.65, 51.97),
    56: (5.70, 51.98),
    57: (5.75, 51.99),
    58: (5.80, 52.00),
    59: (5.85, 51.01),
    60: (5.90, 51.02),
}
_STEDIN_DEFAULT_CENTROID = (4.48, 51.92)  # Rotterdam


def stedin_source_dir(data_root: Path | None = None) -> Path:
    cfg = get_worker_config()
    base = Path(data_root) if data_root is not None else Path(cfg.data_raw_path)
    return base / STEDIN_SUBDIR


def has_stedin_files(data_root: Path | None = None) -> bool:
    directory = stedin_source_dir(data_root)
    return directory.is_dir() and bool(list(directory.glob(STEDIN_GLOB)))


def _slug(value: str, max_len: int = 24) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return cleaned[:max_len] or "SEG"



def _external_ref(postcode: str, street: str, city: str) -> str:
    key = f"{postcode}|{street.strip()}|{city.strip()}".upper()
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"STEDIN-{digest.upper()}"


def _postcode_to_lonlat(postcode: str, city: str) -> tuple[float, float]:
    """Approximate WGS84 from Dutch postcode (PC2 centroid + PC4 jitter)."""
    pc = postcode.replace(" ", "").upper()
    pc4 = int(pc[:4]) if len(pc) >= 4 and pc[:4].isdigit() else 3011
    pc2 = pc4 // 100
    base_lon, base_lat = _NL_PC2_CENTROIDS.get(pc2, _STEDIN_DEFAULT_CENTROID)
    lon = base_lon + ((pc4 % 100) // 10) * 0.0015 + (pc4 % 10) * 0.00015
    lat = base_lat + ((pc4 // 10) % 10) * 0.001 + (pc4 % 10) * 0.0001
    return round(lon, 6), round(lat, 6)


def _read_stedin_file(path: Path) -> pl.DataFrame:
    header = path.read_text(encoding="utf-8-sig").splitlines()[0]
    separator = ";" if ";" in header and "\t" not in header else "\t"
    frame = pl.read_csv(
        path,
        separator=separator,
        decimal_comma=True,
        infer_schema_length=5000,
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
    )
    if "SJI_GEMIDDELD" in frame.columns and "SJA_GEMIDDELD" not in frame.columns:
        frame = frame.rename({"SJI_GEMIDDELD": "SJA_GEMIDDELD"})
    elif "SJI_GEMIDDELD" in frame.columns:
        frame = frame.with_columns(
            pl.coalesce([pl.col("SJA_GEMIDDELD"), pl.col("SJI_GEMIDDELD")]).alias("SJA_GEMIDDELD")
        ).drop("SJI_GEMIDDELD")
    return frame


def load_stedin_elk(stedin_dir: Path) -> pl.DataFrame:
    """Load and combine electricity (ELK) rows from all Stedin year files."""
    paths = sorted(stedin_dir.glob(STEDIN_GLOB))
    if not paths:
        raise FileNotFoundError(f"No Stedin CSV files matching {STEDIN_GLOB} in {stedin_dir}")

    frames: list[pl.DataFrame] = []
    for path in paths:
        year_token = path.stem.split()[-1]
        if not year_token.isdigit():
            continue
        year = int(year_token)
        frame = _read_stedin_file(path)
        frame = frame.filter(pl.col("PRODUCTSOORT") == "ELK")
        if frame.is_empty():
            continue
        frames.append(
            frame.with_columns(
                pl.lit(year).alias("year"),
                pl.col("POSTCODE_VAN").cast(pl.Utf8).str.replace_all(" ", "").alias("postcode"),
                pl.col("STRAATNAAM").cast(pl.Utf8).str.strip_chars().alias("street"),
                pl.col("WOONPLAATS").cast(pl.Utf8).str.strip_chars().alias("city"),
                pl.col("SJA_GEMIDDELD").cast(pl.Float64, strict=False).alias("sja_kwh"),
                pl.col("AANSLUITINGEN_AANTAL")
                .cast(pl.Int64, strict=False)
                .fill_null(1)
                .alias("connections"),
            ).select("year", "postcode", "street", "city", "sja_kwh", "connections", "SLIMME_METER_PERC")
        )

    if not frames:
        raise ValueError(f"No ELK (electricity) rows found under {stedin_dir}")

    combined = pl.concat(frames, how="diagonal_relaxed")
    combined = combined.filter(pl.col("sja_kwh").is_not_null() & (pl.col("sja_kwh") > 0))
    return combined


def _build_segment_table(elk: pl.DataFrame) -> pl.DataFrame:
    keyed = elk.with_columns(
        pl.concat_str([pl.col("postcode"), pl.lit("|"), pl.col("street"), pl.lit("|"), pl.col("city")])
        .str.to_uppercase()
        .alias("segment_key")
    )

    pivoted = (
        keyed.group_by("segment_key", "postcode", "street", "city")
        .agg(
            pl.col("connections").max().alias("connections"),
            pl.col("sja_kwh").filter(pl.col("year") == 2024).mean().alias("sja_2024"),
            pl.col("sja_kwh").filter(pl.col("year") == 2025).mean().alias("sja_2025"),
            pl.col("sja_kwh").filter(pl.col("year") == 2026).mean().alias("sja_2026"),
            pl.col("SLIMME_METER_PERC").mean().alias("smart_meter_pct"),
        )
        .with_columns(
            pl.coalesce([pl.col("sja_2026"), pl.col("sja_2025"), pl.col("sja_2024")]).alias("sja_latest"),
            pl.coalesce([pl.col("sja_2024"), pl.col("sja_2025"), pl.col("sja_2026")]).alias("sja_baseline"),
        )
        .filter(pl.col("sja_latest").is_not_null())
        .sort("connections", descending=True)
    )

    if pivoted.height > MAX_SEGMENTS:
        pivoted = pivoted.head(MAX_SEGMENTS)
    return pivoted.unique(subset=["segment_key"], keep="first")


def _hourly_profile(
    baseline_annual_kwh: float,
    recent_annual_kwh: float,
    hours: int,
    seed: int,
) -> list[tuple[datetime, float]]:
    """Build hourly consumption; recent window reflects latest-year SJA vs baseline."""
    rng = np.random.default_rng(seed)
    end = datetime(2026, 6, 1, tzinfo=UTC)
    start = end - timedelta(hours=hours - 1)

    baseline_hourly = baseline_annual_kwh / 8760.0
    recent_hourly = recent_annual_kwh / 8760.0
    recent_hours = max(int(hours * 0.25), 336)  # align with feature recent window
    split_idx = hours - recent_hours

    rows: list[tuple[datetime, float]] = []
    ts = start
    for idx in range(hours):
        hour = ts.hour
        day_frac = ts.timetuple().tm_yday / 365.0
        seasonal = 1.0 + 0.15 * np.sin(2 * np.pi * day_frac)
        if hour < 7 or hour > 22:
            diurnal = 0.45
        elif 17 <= hour <= 21:
            diurnal = 1.1
        else:
            diurnal = 0.85
        base = baseline_hourly if idx < split_idx else recent_hourly
        noise = float(rng.normal(1.0, 0.04))
        kwh = max(base * seasonal * diurnal * noise, 0.0)
        rows.append((ts, kwh))
        ts += timedelta(hours=1)

    total = sum(k for _, k in rows)
    target = baseline_annual_kwh * (split_idx / 8760.0) + recent_annual_kwh * (recent_hours / 8760.0)
    if total > 0 and target > 0:
        scale = target / total
        rows = [(t, k * scale) for t, k in rows]
    return rows


def transform_stedin_to_production(
    data_root: Path | str | None = None,
) -> dict:
    """Write ``data/raw/production/*.csv`` from Stedin open-data files."""
    cfg = get_worker_config()
    base = Path(data_root) if data_root is not None else Path(cfg.data_raw_path)
    src = base / STEDIN_SUBDIR
    out_root = base / PRODUCTION_SUBDIR
    out_root.mkdir(parents=True, exist_ok=True)

    elk = load_stedin_elk(src)
    segments = _build_segment_table(elk)
    log_event(
        logger,
        "stedin_segments_selected",
        source_rows=elk.height,
        segments=segments.height,
        max_segments=MAX_SEGMENTS,
        profile_hours=PROFILE_HOURS,
    )

    pl.DataFrame(
        [{"name": OPERATOR_NAME, "country_code": "NLD", "timezone": "Europe/Amsterdam", "default_currency": "EUR"}]
    ).write_csv(out_root / "operators.csv")

    cities = segments.select("city").unique().sort("city")
    region_rows = [
        {
            "code": f"STEDIN-{_slug(c['city'], 16)}",
            "name": c["city"],
            "region_type": "municipality",
            "operator_name": OPERATOR_NAME,
            "parent_code": "STEDIN-NL",
        }
        for c in cities.iter_rows(named=True)
    ]
    region_rows.insert(
        0,
        {
            "code": "STEDIN-NL",
            "name": "Stedin Netbeheer",
            "region_type": "country",
            "operator_name": OPERATOR_NAME,
            "parent_code": "",
        },
    )
    pl.DataFrame(region_rows).write_csv(out_root / "regions.csv")

    pc4_groups = (
        segments.with_columns(pl.col("postcode").str.slice(0, 4).alias("pc4"))
        .group_by("pc4")
        .agg(pl.col("city").first().alias("city"), pl.len().alias("segments"))
        .sort("segments", descending=True)
    )

    grid_rows: list[dict] = []
    for row in pc4_groups.iter_rows(named=True):
        pc4 = row["pc4"]
        lon, lat = _postcode_to_lonlat(f"{pc4}AA", row["city"])
        feeder_id = f"FD-{pc4}"
        tx_id = f"TX-{pc4}"
        grid_rows.append(
            {
                "external_id": feeder_id,
                "asset_type": "feeder",
                "name": f"Feeder {pc4}",
                "operator_name": OPERATOR_NAME,
                "lon": lon,
                "lat": lat,
                "parent_external_id": "",
                "voltage_level": "lv",
                "capacity_kva": "",
            }
        )
        grid_rows.append(
            {
                "external_id": tx_id,
                "asset_type": "transformer",
                "name": f"Transformer {pc4}",
                "operator_name": OPERATOR_NAME,
                "lon": lon,
                "lat": lat,
                "parent_external_id": feeder_id,
                "voltage_level": "lv",
                "capacity_kva": 630,
            }
        )
    pl.DataFrame(grid_rows).write_csv(out_root / "grid_assets.csv")

    customer_rows: list[dict] = []
    meter_rows: list[dict] = []
    recent_hours = max(int(PROFILE_HOURS * 0.25), 336)
    profile_end = datetime(2026, 6, 1, tzinfo=UTC)
    recent_cutoff = profile_end - timedelta(hours=recent_hours - 1)

    for row in segments.iter_rows(named=True):
        postcode = row["postcode"]
        street = row["street"]
        city = row["city"]
        pc4 = postcode[:4]
        tx_id = f"TX-{pc4}"
        feeder_id = f"FD-{pc4}"
        external_ref = _external_ref(postcode, street, city)
        lon, lat = _postcode_to_lonlat(postcode, city)

        baseline = float(row["sja_baseline"] or row["sja_latest"])
        latest = float(row["sja_latest"])
        drop_ratio = latest / baseline if baseline > 0 else 1.0
        incident = ""
        is_ntl = "false"
        if drop_ratio < 0.85:
            incident = "consumption_drop"
            is_ntl = "true"

        # SJA is kWh per connection; each row is one street segment at typical load.
        annual_unexplained = max(0.0, baseline - latest)
        hourly_unexplained = annual_unexplained / recent_hours if recent_hours > 0 else 0.0

        customer_rows.append(
            {
                "external_ref": external_ref,
                "customer_type": "residential",
                "operator_name": OPERATOR_NAME,
                "lon": lon,
                "lat": lat,
                "transformer_external_id": tx_id,
                "feeder_external_id": feeder_id,
                "region_code": f"STEDIN-{_slug(city, 16)}",
                "zipcode": postcode,
                "baseline_annual_kwh": round(baseline, 2),
                "building_type": "unknown",
                "tariff_type": "single",
                "incident": incident,
                "is_ntl": is_ntl,
            }
        )

        seed = int(hashlib.md5(external_ref.encode()).hexdigest()[:8], 16)
        profile = _hourly_profile(baseline, latest, PROFILE_HOURS, seed)
        for ts, kwh in profile:
            unexplained = hourly_unexplained if ts >= recent_cutoff else 0.0
            meter_rows.append(
                {
                    "customer_external_ref": external_ref,
                    "timestamp": ts.isoformat().replace("+00:00", "Z"),
                    "consumption_kwh": round(kwh, 6),
                    "unexplained_kwh": round(unexplained, 6),
                    "voltage": 230,
                    "power_factor": "",
                    "reading_quality": "good",
                    "source": "stedin_open_data",
                }
            )

    pl.DataFrame(customer_rows).write_csv(out_root / "customers.csv")

    pl.DataFrame(meter_rows).write_csv(out_root / "meter_readings.csv")

    # Aggregate customer load per transformer timestamp for reconciliation layers.
    meter_frame = pl.DataFrame(meter_rows).join(
        pl.DataFrame(customer_rows).select(
            pl.col("external_ref").alias("customer_external_ref"),
            pl.col("transformer_external_id"),
        ),
        on="customer_external_ref",
        how="left",
    ).with_columns(pl.col("unexplained_kwh").fill_null(0.0))
    tx_hourly = (
        meter_frame.group_by("transformer_external_id", "timestamp")
        .agg(
            pl.col("consumption_kwh").sum().alias("load_kwh"),
            pl.col("unexplained_kwh").sum().alias("unexplained_kwh"),
        )
        .sort("transformer_external_id", "timestamp")
    )

    asset_energy_rows = [
        {
            "asset_external_id": row["transformer_external_id"],
            "timestamp": row["timestamp"],
            "energy_input_kwh": round(
                float(row["load_kwh"]) * 1.04 + float(row["unexplained_kwh"]),
                6,
            ),
            "energy_output_kwh": "",
            "reading_quality": "good",
            "source": "stedin_derived",
        }
        for row in tx_hourly.iter_rows(named=True)
        if row["transformer_external_id"]
    ]
    tech_loss_rows = [
        {
            "asset_external_id": row["transformer_external_id"],
            "timestamp": row["timestamp"],
            "estimated_technical_loss_kwh": round(float(row["load_kwh"]) * 0.04, 6),
            "method": "loss_factor",
            "confidence": 0.75,
            "model_version": "stedin-v1",
        }
        for row in tx_hourly.iter_rows(named=True)
        if row["transformer_external_id"]
    ]

    pl.DataFrame(asset_energy_rows).write_csv(out_root / "asset_energy_readings.csv")
    pl.DataFrame(tech_loss_rows).write_csv(out_root / "technical_loss_estimates.csv")

    summary = {
        "source_dir": str(src),
        "output_dir": str(out_root),
        "segments": segments.height,
        "customers": len(customer_rows),
        "meter_readings": len(meter_rows),
        "grid_assets": len(grid_rows),
        "profile_hours": PROFILE_HOURS,
    }
    log_event(logger, "stedin_transform_complete", **summary)
    return summary
