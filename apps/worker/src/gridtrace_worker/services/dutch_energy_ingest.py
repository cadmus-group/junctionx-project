"""Ingest Dutch DSO street-level electricity context (Liander or Stedin)."""

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
STEDIN_DIR = "stedin"
STEDIN_GLOB = "stedin_kleinverbruik_*.csv"
STEDIN_ROOT_GLOB = "Stedin kleinverbruikgegevens *.csv"
STEDIN_COLUMNS = (
    "POSTCODE_VAN",
    "WOONPLAATS",
    "PRODUCTSOORT",
    "AANSLUITINGEN_AANTAL",
    "LEVERINGSRICHTING_PERC",
    "SJA_GEMIDDELD",
    "SLIMME_METER_PERC",
)

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


def resolve_dutch_energy_source(
    *,
    data_raw_path: str | Path,
    explicit: str | None = None,
) -> str:
    """Pick Liander vs Stedin: explicit env, then auto-detect from files on disk."""
    if explicit in {"liander", "stedin"}:
        return explicit

    raw = Path(data_raw_path)
    if list_stedin_csv_paths(raw):
        return "stedin"
    if (raw / LIANDER_FILENAME).is_file():
        return "liander"
    return "stedin"


def list_stedin_csv_paths(data_raw_path: str | Path) -> list[Path]:
    """Return sorted Stedin kleinverbruik CSV paths under ``data/raw``."""
    raw = Path(data_raw_path)
    paths = sorted((raw / STEDIN_DIR).glob(STEDIN_GLOB))
    if paths:
        return paths
    return sorted(raw.glob(STEDIN_ROOT_GLOB))


def resolve_dutch_energy_csv_paths(
    *,
    data_raw_path: str | Path,
    source: str,
    csv_path: str | Path | None = None,
) -> list[Path]:
    if csv_path is not None:
        path = Path(csv_path)
        if path.is_dir():
            nested = sorted(path.glob(STEDIN_GLOB))
            if nested:
                return nested
            liander = path / LIANDER_FILENAME
            if liander.is_file():
                return [liander]
            matches = sorted(path.glob("*.csv"))
            if not matches:
                raise FileNotFoundError(f"No CSV files found under {path}")
            return matches
        return [path]

    raw = Path(data_raw_path)
    if source == "stedin":
        paths = list_stedin_csv_paths(raw)
        if not paths:
            raise FileNotFoundError(
                f"No Stedin kleinverbruik CSVs under {raw / STEDIN_DIR}. "
                "Run scripts/setup-stedin-data.sh or place "
                "stedin_kleinverbruik_YYYY.csv files there."
            )
        return paths

    liander = raw / LIANDER_FILENAME
    if not liander.is_file():
        raise FileNotFoundError(
            f"Liander CSV not found at {liander}. "
            "Download from Kaggle (lucabasa/dutch-energy) and place it under DATA_RAW_PATH."
        )
    return [liander]


class DutchEnergySpatialIngestion:
    """Load Dutch energy spatial baselines with Polars and upsert into PostGIS."""

    def __init__(
        self,
        csv_path: Path | str | None = None,
        *,
        source: str | None = None,
    ) -> None:
        cfg = get_worker_config()
        raw_source = source if source is not None else cfg.dutch_energy_source
        self.source = resolve_dutch_energy_source(
            data_raw_path=cfg.data_raw_path,
            explicit=None if raw_source in (None, "auto") else raw_source,
        )
        self.csv_paths = resolve_dutch_energy_csv_paths(
            data_raw_path=cfg.data_raw_path,
            source=self.source,
            csv_path=csv_path,
        )
        self._frame: pl.DataFrame | None = None

    @property
    def csv_path(self) -> Path:
        return self.csv_paths[0]

    def _read_liander(self, path: Path) -> pl.DataFrame:
        return pl.read_csv(path)

    def _read_stedin(self, path: Path) -> pl.DataFrame:
        header = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        separator = ";" if ";" in header else "\t"
        df = pl.read_csv(
            path,
            separator=separator,
            decimal_comma=True,
            truncate_ragged_lines=True,
            infer_schema_length=10_000,
        )
        for column in STEDIN_COLUMNS:
            if column not in df.columns:
                df = df.with_columns(pl.lit(None).alias(column))
        return df.select(STEDIN_COLUMNS)

    def _read_raw(self) -> pl.DataFrame:
        if self.source == "stedin":
            return pl.concat([self._read_stedin(path) for path in self.csv_paths], how="vertical")
        return self._read_liander(self.csv_paths[0])

    def _normalize_liander(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.col("zipcode_from")
            .cast(pl.Utf8)
            .str.replace_all(" ", "")
            .str.to_uppercase()
            .alias("zipcode"),
            pl.col("city").cast(pl.Utf8).str.to_lowercase().alias("city_norm"),
            pl.col("num_connections")
            .cast(pl.Int64, strict=False)
            .fill_null(1)
            .alias("weight"),
        )

    def _normalize_stedin(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.filter(pl.col("PRODUCTSOORT") == "ELK")
            .with_columns(
                pl.col("POSTCODE_VAN")
                .cast(pl.Utf8)
                .str.replace_all(" ", "")
                .str.to_uppercase()
                .alias("zipcode"),
                pl.col("WOONPLAATS").cast(pl.Utf8).str.to_lowercase().alias("city_norm"),
                pl.col("AANSLUITINGEN_AANTAL")
                .cast(pl.Int64, strict=False)
                .fill_null(1)
                .alias("weight"),
            )
        )

    def _aggregate_by_zipcode(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.source == "stedin":
            projected = df.select(
                "zipcode",
                pl.col("SJA_GEMIDDELD").cast(pl.Float32).alias("baseline_annual_kwh"),
                pl.col("SLIMME_METER_PERC").cast(pl.Float32).alias("street_smartmeter_perc"),
                (pl.col("LEVERINGSRICHTING_PERC") < 95.0).alias("has_solar_potential"),
            )
        else:
            projected = df.select(
                "zipcode",
                pl.col("annual_consume").cast(pl.Float32).alias("baseline_annual_kwh"),
                pl.col("smartmeter_perc").cast(pl.Float32).alias("street_smartmeter_perc"),
                (pl.col("delivery_perc") < 95.0).alias("has_solar_potential"),
            )

        return (
            projected.drop_nulls(
                subset=["zipcode", "baseline_annual_kwh", "street_smartmeter_perc"]
            )
            .group_by("zipcode")
            .agg(
                pl.col("baseline_annual_kwh").mean(),
                pl.col("street_smartmeter_perc").mean(),
                pl.col("has_solar_potential").any(),
            )
        )

    def process_with_polars(self) -> pl.DataFrame:
        """Read source CSV(s), project columns, and derive solar potential flag."""
        raw = self._read_raw()
        if self.source == "stedin":
            normalized = self._normalize_stedin(raw)
        else:
            normalized = self._normalize_liander(raw)

        df = self._aggregate_by_zipcode(normalized)
        self._frame = df
        return df

    def zipcode_weights(self, *, sample_city: str | None = None) -> list[tuple[str, int]]:
        """Zipcodes weighted by connection count for deterministic demo assignment."""
        raw = self._read_raw()
        if self.source == "stedin":
            normalized = self._normalize_stedin(raw)
        else:
            normalized = self._normalize_liander(raw)

        city = sample_city
        if city is None:
            city = "rotterdam" if self.source == "stedin" else "amsterdam"

        filtered = normalized.filter(pl.col("city_norm") == city).select("zipcode", "weight")
        if filtered.is_empty():
            filtered = normalized.select("zipcode", "weight")

        grouped = (
            filtered.group_by("zipcode")
            .agg(pl.col("weight").sum())
            .sort("weight", descending=True)
        )
        return [(row["zipcode"], int(row["weight"])) for row in grouped.to_dicts()]

    def assign_customer_zipcodes(self, session: Session, seed: int) -> int:
        """Map demo customers to DSO zipcodes (deterministic, weighted sampling)."""
        weights = self.zipcode_weights()
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

        async with AsyncSessionLocal() as session, session.begin():
            await session.execute(_UPDATE_CUSTOMERS, records)

        return len(records)

    def run(self, session: Session, seed: int) -> dict[str, int | str | list[str]]:
        """Assign zipcodes, upsert street baselines, return summary counts."""
        missing = [str(path) for path in self.csv_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Dutch energy CSV(s) not found: {', '.join(missing)}")

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
            "source": self.source,
            "csv_paths": [str(path) for path in self.csv_paths],
            "zipcodes_assigned": assigned,
            "street_rows_processed": street_rows,
            "customers_enriched": int(enriched or 0),
        }
