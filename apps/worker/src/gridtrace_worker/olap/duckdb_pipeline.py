"""DuckDB OLAP layer over local Parquet files.

Exports meter readings from PostgreSQL, merges NED macro baselines, and computes
rolling analytics (14-day averages, peer-group medians by Woningwaarde tier, daylight
drop indices) for the background scoring pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl
from gridtrace_api.db.models import Customer, MeterReading
from sqlalchemy import select
from sqlalchemy.orm import Session


def parquet_paths(processed_root: Path | str) -> dict[str, Path]:
    root = Path(processed_root)
    root.mkdir(parents=True, exist_ok=True)
    return {
        "meter_readings": root / "meter_readings.parquet",
        "ned_grid_status": root / "ned_grid_status.parquet",
        "customer_features": root / "customer_features.parquet",
    }


def export_meter_readings(session: Session, out_path: Path) -> int:
    rows = session.execute(
        select(
            MeterReading.meter_id,
            MeterReading.timestamp,
            MeterReading.consumption_kwh,
            MeterReading.reading_quality,
        ).order_by(MeterReading.meter_id, MeterReading.timestamp)
    ).all()
    frame = pl.DataFrame(
        {
            "meter_id": [r[0] for r in rows],
            "timestamp": [r[1] for r in rows],
            "kwh_consumed": [float(r[2]) for r in rows],
            "is_estimated": [r[3] != "good" for r in rows],
        }
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(out_path)
    return frame.height


def write_ned_parquet(records: list[dict[str, Any]], out_path: Path) -> int:
    if not records:
        frame = pl.DataFrame(
            schema={
                "timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
                "national_load_mw": pl.Float64,
                "production_mix_solar": pl.Float64,
                "production_mix_wind": pl.Float64,
                "grid_status_flag": pl.Utf8,
            }
        )
    else:
        frame = pl.DataFrame(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(out_path)
    return frame.height


def compute_customer_features(
    processed_root: Path | str,
    customers: list[Customer],
) -> pl.DataFrame:
    """Run DuckDB window analytics over exported Parquet."""
    paths = parquet_paths(processed_root)
    if not paths["meter_readings"].is_file():
        return pl.DataFrame()

    customer_ctx = pl.DataFrame(
        {
            "meter_id": [c.id for c in customers],
            "woningwaarde_category": [c.woningwaarde_category or "unknown" for c in customers],
            "solar_potential_flag": [bool(c.solar_potential_flag) for c in customers],
        }
    )
    ctx_path = Path(processed_root) / "_customer_ctx.parquet"
    customer_ctx.write_parquet(ctx_path)

    conn = duckdb.connect()
    try:
        query = f"""
        WITH readings AS (
            SELECT
                meter_id,
                timestamp,
                kwh_consumed,
                EXTRACT(HOUR FROM timestamp) AS hour_of_day
            FROM read_parquet('{paths["meter_readings"]}')
        ),
        ctx AS (
            SELECT * FROM read_parquet('{ctx_path}')
        ),
        enriched AS (
            SELECT r.*, c.woningwaarde_category, c.solar_potential_flag
            FROM readings r
            JOIN ctx c ON r.meter_id = c.meter_id
        ),
        rolling AS (
            SELECT
                meter_id,
                timestamp,
                kwh_consumed,
                hour_of_day,
                woningwaarde_category,
                solar_potential_flag,
                AVG(kwh_consumed) OVER (
                    PARTITION BY meter_id
                    ORDER BY timestamp
                    ROWS BETWEEN 335 PRECEDING AND CURRENT ROW
                ) AS rolling_14d_avg_kwh,
                MEDIAN(kwh_consumed) OVER (
                    PARTITION BY woningwaarde_category, hour_of_day
                    ORDER BY timestamp
                    ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
                ) AS peer_group_median_kwh
            FROM enriched
        ),
        latest AS (
            SELECT *
            FROM rolling
            QUALIFY ROW_NUMBER() OVER (PARTITION BY meter_id ORDER BY timestamp DESC) = 1
        )
        SELECT
            meter_id,
            rolling_14d_avg_kwh,
            peer_group_median_kwh,
            CASE
                WHEN hour_of_day BETWEEN 8 AND 18
                     AND kwh_consumed < 0.5 * peer_group_median_kwh
                THEN 1.0 - (kwh_consumed / NULLIF(peer_group_median_kwh, 0))
                ELSE 0.0
            END AS daylight_drop_index,
            solar_potential_flag,
            woningwaarde_category
        FROM latest
        """
        return conn.execute(query).pl()
    finally:
        conn.close()
        ctx_path.unlink(missing_ok=True)


def persist_feature_parquet(frame: pl.DataFrame, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(out_path)
    return frame.height
