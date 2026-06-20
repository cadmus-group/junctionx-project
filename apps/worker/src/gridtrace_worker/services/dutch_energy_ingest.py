"""Ingest Liander street-level electricity context (Kaggle / Luca Basanisi dataset)."""

from __future__ import annotations

import random
from pathlib import Path

import polars as pl
from gridtrace_api.db.models import Customer
from gridtrace_api.db.session import AsyncSessionLocal
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from gridtrace_worker.config import get_worker_config

LIANDER_FILENAME = "liander_electricity_01012020.csv"

_UPDATE_CUSTOMERS = text(
    """
    UPDATE customers
    SET baseline_annual_kwh = :baseline_annual_kwh,
        street_smartmeter_perc = :street_smartmeter_perc,
        solar_potential_flag = :solar_potential_flag
    WHERE zipcode = :zipcode
    """
)

_ASSIGN_ZIPCODE = text(
    """
    UPDATE customers
    SET zipcode = :zipcode
    WHERE id = :id
    """
)


def _normalize_zipcode(value: str) -> str:
    return value.replace(" ", "").upper()


class DutchEnergySpatialIngestion:
    """Load Dutch energy spatial baselines with Polars and upsert into PostGIS."""

    def __init__(self, csv_path: Path | str | None = None) -> None:
        if csv_path is not None:
            self.csv_path = Path(csv_path)
        else:
            cfg = get_worker_config()
            self.csv_path = Path(cfg.data_raw_path) / LIANDER_FILENAME
        self._frame: pl.DataFrame | None = None

    def _read_raw(self) -> pl.DataFrame:
        return pl.read_csv(self.csv_path)

    def process_with_polars(self) -> pl.DataFrame:
        """Read Liander CSV, project columns, and derive solar potential flag."""
        df = (
            self._read_raw()
            .with_columns(
                pl.col("zipcode_from")
                .cast(pl.Utf8)
                .str.replace_all(" ", "")
                .str.to_uppercase()
                .alias("zipcode")
            )
            .select(
                "zipcode",
                pl.col("annual_consume").cast(pl.Float32).alias("baseline_annual_kwh"),
                pl.col("smartmeter_perc").cast(pl.Float32).alias("street_smartmeter_perc"),
                (pl.col("delivery_perc") < 95.0).alias("has_solar_potential"),
            )
            .drop_nulls(subset=["zipcode", "baseline_annual_kwh", "street_smartmeter_perc"])
            .group_by("zipcode")
            .agg(
                pl.col("baseline_annual_kwh").mean(),
                pl.col("street_smartmeter_perc").mean(),
                pl.col("has_solar_potential").any(),
            )
        )
        self._frame = df
        return df

    def amsterdam_zipcode_weights(self) -> list[tuple[str, int]]:
        """Zipcodes in Amsterdam weighted by connection count (for demo assignment)."""
        raw = self._read_raw().with_columns(
            pl.col("zipcode_from")
            .cast(pl.Utf8)
            .str.replace_all(" ", "")
            .str.to_uppercase()
            .alias("zipcode"),
            pl.col("city").cast(pl.Utf8).str.to_lowercase().alias("city_norm"),
            pl.col("num_connections").cast(pl.Int64, strict=False).fill_null(1).alias("weight"),
        )
        amsterdam = raw.filter(pl.col("city_norm") == "amsterdam").select("zipcode", "weight")
        if amsterdam.is_empty():
            amsterdam = raw.select("zipcode", "weight")

        grouped = (
            amsterdam.group_by("zipcode")
            .agg(pl.col("weight").sum())
            .sort("weight", descending=True)
        )
        return [(row["zipcode"], int(row["weight"])) for row in grouped.to_dicts()]

    def assign_customer_zipcodes(self, session: Session, seed: int) -> int:
        """Map demo customers to Liander zipcodes (deterministic, weighted sampling)."""
        weights = self.amsterdam_zipcode_weights()
        if not weights:
            return 0

        zipcodes = [zc for zc, _ in weights]
        weight_values = [w for _, w in weights]
        customer_ids = session.scalars(
            select(Customer.id).where(Customer.zipcode.is_(None))
        ).all()
        if not customer_ids:
            return 0

        rng = random.Random(seed)
        records = [
            {"id": customer_id, "zipcode": rng.choices(zipcodes, weights=weight_values, k=1)[0]}
            for customer_id in customer_ids
        ]
        session.execute(_ASSIGN_ZIPCODE, records)
        return len(records)

    def sink_to_postgis_sync(self, session: Session, df: pl.DataFrame | None = None) -> int:
        """Batch-update customers in the caller's transaction (worker default)."""
        frame = df if df is not None else self._frame
        if frame is None:
            frame = self.process_with_polars()

        records = frame.to_dicts()
        for record in records:
            record["solar_potential_flag"] = record.pop("has_solar_potential")

        session.execute(_UPDATE_CUSTOMERS, records)
        return len(records)

    async def sink_to_postgis(self, df: pl.DataFrame | None = None) -> int:
        """Batch-update customers matched by zipcode (standalone async entrypoint)."""
        frame = df if df is not None else self._frame
        if frame is None:
            frame = self.process_with_polars()

        records = frame.to_dicts()
        for record in records:
            record["solar_potential_flag"] = record.pop("has_solar_potential")

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(_UPDATE_CUSTOMERS, records)

        return len(records)

    def run(self, session: Session, seed: int) -> dict[str, int | str]:
        """Assign zipcodes, upsert Liander baselines, return summary counts."""
        if not self.csv_path.is_file():
            raise FileNotFoundError(
                f"Liander CSV not found at {self.csv_path}. "
                "Download from Kaggle (lucabasa/dutch-energy) and place it under DATA_RAW_PATH."
            )

        assigned = self.assign_customer_zipcodes(session, seed)
        session.flush()
        street_rows = self.sink_to_postgis_sync(session)
        session.flush()
        enriched = session.scalar(
            text(
                "SELECT COUNT(*) FROM customers "
                "WHERE baseline_annual_kwh IS NOT NULL"
            )
        )
        return {
            "csv_path": str(self.csv_path),
            "zipcodes_assigned": assigned,
            "street_rows_processed": street_rows,
            "customers_enriched": int(enriched or 0),
        }
