"""Import operational grid data from CSV files under ``data/raw/production/``.

Expected layout (filenames are fixed):

    data/raw/production/
      operators.csv
      regions.csv              # optional
      grid_assets.csv
      customers.csv
      meter_readings.csv
      asset_energy_readings.csv  # optional

See ``docs/ingest-spec.md`` for column definitions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from geoalchemy2.shape import from_shape
from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    GridAsset,
    MeterReading,
    Operator,
    Region,
    TechnicalLossEstimate,
)
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from gridtrace_worker.config import get_worker_config

PRODUCTION_SUBDIR = "production"
READINGS_CHUNK = 5000

OPERATORS_FILE = "operators.csv"
REGIONS_FILE = "regions.csv"
GRID_ASSETS_FILE = "grid_assets.csv"
CUSTOMERS_FILE = "customers.csv"
METER_READINGS_FILE = "meter_readings.csv"
ASSET_ENERGY_FILE = "asset_energy_readings.csv"
TECHNICAL_LOSS_FILE = "technical_loss_estimates.csv"


def _point(lon: float, lat: float):
    return from_shape(Point(lon, lat), srid=4326)


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...], label: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _truthy(value: object) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _customer_metadata(row: dict) -> dict:
    metadata: dict = {"source": "production_csv"}
    incident = str(row.get("incident") or "").strip()
    if incident:
        metadata["incident"] = incident
    if row.get("is_ntl") not in (None, ""):
        metadata["is_ntl"] = _truthy(row.get("is_ntl"))
    return metadata


def _parse_timestamps(frame: pl.DataFrame, column: str = "timestamp") -> pl.DataFrame:
    if frame.schema[column] == pl.Utf8:
        return frame.with_columns(
            pl.col(column).str.to_datetime(time_zone="UTC", strict=False).alias(column)
        )
    return frame.with_columns(pl.col(column).cast(pl.Datetime(time_zone="UTC")).alias(column))


class ProductionIngest:
    """Load CSV master data and readings into Postgres (idempotent upserts)."""

    def __init__(self, data_root: str | Path | None = None) -> None:
        cfg = get_worker_config()
        base = Path(data_root) if data_root is not None else Path(cfg.data_raw_path)
        self.root = base / PRODUCTION_SUBDIR

    def csv_path(self, filename: str) -> Path:
        return self.root / filename

    def require_csv(self, filename: str) -> Path:
        path = self.csv_path(filename)
        if not path.is_file():
            raise FileNotFoundError(
                f"Required CSV not found: {path}. "
                f"See docs/ingest-spec.md and place files under data/raw/production/."
            )
        return path

    def optional_csv(self, filename: str) -> Path | None:
        path = self.csv_path(filename)
        return path if path.is_file() else None

    def ingest_operators(self, session: Session) -> dict[str, str]:
        path = self.require_csv(OPERATORS_FILE)
        frame = pl.read_csv(path)
        _require_columns(frame, ("name", "country_code"), OPERATORS_FILE)

        id_by_name: dict[str, str] = {}
        inserted = updated = 0
        for row in frame.iter_rows(named=True):
            name = str(row["name"]).strip()
            if not name:
                continue
            existing = session.execute(
                select(Operator).where(Operator.name == name)
            ).scalar_one_or_none()
            if existing:
                existing.country_code = str(row["country_code"]).strip()
                existing.timezone = str(row.get("timezone") or "Europe/Amsterdam")
                existing.default_currency = str(row.get("default_currency") or "EUR")
                id_by_name[name] = existing.id
                updated += 1
            else:
                op = Operator(
                    id=str(uuid.uuid4()),
                    name=name,
                    country_code=str(row["country_code"]).strip(),
                    timezone=str(row.get("timezone") or "Europe/Amsterdam"),
                    default_currency=str(row.get("default_currency") or "EUR"),
                )
                session.add(op)
                session.flush()
                id_by_name[name] = op.id
                inserted += 1
        session.flush()
        return {"inserted": inserted, "updated": updated, "ids_by_name": id_by_name}

    def ingest_regions(self, session: Session, operator_ids: dict[str, str]) -> dict[str, str]:
        path = self.optional_csv(REGIONS_FILE)
        if path is None:
            return {"skipped": True, "codes": {}}

        frame = pl.read_csv(path)
        _require_columns(frame, ("code", "name", "region_type", "operator_name"), REGIONS_FILE)

        code_to_id: dict[str, str] = {}
        inserted = updated = 0
        for row in frame.iter_rows(named=True):
            code = str(row["code"]).strip()
            op_name = str(row["operator_name"]).strip()
            operator_id = operator_ids.get(op_name)
            if not code or not operator_id:
                continue
            parent_code = str(row.get("parent_code") or "").strip() or None
            parent_id = code_to_id.get(parent_code) if parent_code else None

            existing = session.execute(
                select(Region).where(Region.operator_id == operator_id, Region.code == code)
            ).scalar_one_or_none()
            if existing:
                existing.name = str(row["name"]).strip()
                existing.region_type = str(row["region_type"]).strip()
                existing.parent_region_id = parent_id
                code_to_id[code] = existing.id
                updated += 1
            else:
                region = Region(
                    id=str(uuid.uuid4()),
                    operator_id=operator_id,
                    parent_region_id=parent_id,
                    region_type=str(row["region_type"]).strip(),
                    code=code,
                    name=str(row["name"]).strip(),
                    geometry=None,
                    properties_json={},
                )
                session.add(region)
                session.flush()
                code_to_id[code] = region.id
                inserted += 1
        session.flush()
        return {"inserted": inserted, "updated": updated, "codes": code_to_id}

    def ingest_grid_assets(self, session: Session, operator_ids: dict[str, str]) -> dict[str, str]:
        path = self.require_csv(GRID_ASSETS_FILE)
        frame = pl.read_csv(path)
        _require_columns(
            frame,
            ("external_id", "asset_type", "name", "operator_name", "lon", "lat"),
            GRID_ASSETS_FILE,
        )

        external_to_id: dict[str, str] = {}
        inserted = updated = 0
        # Pass 1: create/update without parent links
        for row in frame.iter_rows(named=True):
            external_id = str(row["external_id"]).strip()
            op_name = str(row["operator_name"]).strip()
            operator_id = operator_ids.get(op_name)
            if not external_id or not operator_id:
                continue

            lon = float(row["lon"])
            lat = float(row["lat"])
            existing = session.execute(
                select(GridAsset).where(
                    GridAsset.operator_id == operator_id,
                    GridAsset.external_id == external_id,
                )
            ).scalar_one_or_none()
            if existing:
                existing.asset_type = str(row["asset_type"]).strip()
                existing.name = str(row["name"]).strip()
                existing.voltage_level = (
                    str(row["voltage_level"]).strip() if row.get("voltage_level") else None
                )
                existing.capacity_kva = (
                    float(row["capacity_kva"]) if row.get("capacity_kva") not in (None, "") else None
                )
                existing.geometry = _point(lon, lat)
                external_to_id[external_id] = existing.id
                updated += 1
            else:
                asset = GridAsset(
                    id=str(uuid.uuid4()),
                    operator_id=operator_id,
                    parent_asset_id=None,
                    asset_type=str(row["asset_type"]).strip(),
                    external_id=external_id,
                    name=str(row["name"]).strip(),
                    voltage_level=(
                        str(row["voltage_level"]).strip() if row.get("voltage_level") else None
                    ),
                    capacity_kva=(
                        float(row["capacity_kva"]) if row.get("capacity_kva") not in (None, "") else None
                    ),
                    region_id=None,
                    geometry=_point(lon, lat),
                    properties_json={},
                )
                session.add(asset)
                session.flush()
                external_to_id[external_id] = asset.id
                inserted += 1

        # Pass 2: wire parent links
        for row in frame.iter_rows(named=True):
            external_id = str(row["external_id"]).strip()
            parent_external = str(row.get("parent_external_id") or "").strip()
            if not external_id or not parent_external:
                continue
            asset_id = external_to_id.get(external_id)
            parent_id = external_to_id.get(parent_external)
            if asset_id and parent_id:
                asset = session.get(GridAsset, asset_id)
                if asset:
                    asset.parent_asset_id = parent_id

        session.flush()
        return {"inserted": inserted, "updated": updated, "external_ids": external_to_id}

    def ingest_customers(
        self,
        session: Session,
        operator_ids: dict[str, str],
        asset_external_ids: dict[str, str],
        region_codes: dict[str, str],
    ) -> dict[str, str]:
        path = self.require_csv(CUSTOMERS_FILE)
        frame = pl.read_csv(path)
        _require_columns(
            frame,
            ("external_ref", "customer_type", "operator_name", "lon", "lat"),
            CUSTOMERS_FILE,
        )

        ref_to_id: dict[str, str] = {}
        inserted = updated = 0
        for row in frame.iter_rows(named=True):
            external_ref = str(row["external_ref"]).strip()
            op_name = str(row["operator_name"]).strip()
            operator_id = operator_ids.get(op_name)
            if not external_ref or not operator_id:
                continue

            tx_ext = str(row.get("transformer_external_id") or "").strip() or None
            feeder_ext = str(row.get("feeder_external_id") or "").strip() or None
            region_code = str(row.get("region_code") or "").strip() or None

            lon = float(row["lon"])
            lat = float(row["lat"])
            existing = session.execute(
                select(Customer).where(
                    Customer.operator_id == operator_id,
                    Customer.external_ref == external_ref,
                )
            ).scalar_one_or_none()
            fields = {
                "customer_type": str(row["customer_type"]).strip(),
                "tariff_type": str(row.get("tariff_type") or "single").strip(),
                "building_type": (
                    str(row["building_type"]).strip() if row.get("building_type") else None
                ),
                "zipcode": str(row["zipcode"]).strip() if row.get("zipcode") else None,
                "baseline_annual_kwh": (
                    float(row["baseline_annual_kwh"])
                    if row.get("baseline_annual_kwh") not in (None, "")
                    else None
                ),
                "transformer_id": asset_external_ids.get(tx_ext) if tx_ext else None,
                "feeder_id": asset_external_ids.get(feeder_ext) if feeder_ext else None,
                "region_id": region_codes.get(region_code) if region_code else None,
                "geometry": _point(lon, lat),
                "metadata_json": _customer_metadata(row),
            }
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                ref_to_id[external_ref] = existing.id
                updated += 1
            else:
                customer = Customer(
                    id=str(uuid.uuid4()),
                    operator_id=operator_id,
                    external_ref=external_ref,
                    meter_asset_id=None,
                    solar_potential_flag=False,
                    **fields,
                )
                session.add(customer)
                session.flush()
                ref_to_id[external_ref] = customer.id
                inserted += 1
        session.flush()
        return {"inserted": inserted, "updated": updated, "external_refs": ref_to_id}

    def ingest_meter_readings(self, session: Session, customer_refs: dict[str, str]) -> dict:
        path = self.require_csv(METER_READINGS_FILE)
        frame = pl.read_csv(path)
        _require_columns(
            frame,
            ("customer_external_ref", "timestamp", "consumption_kwh"),
            METER_READINGS_FILE,
        )
        frame = _parse_timestamps(frame)

        inserted = skipped = 0
        rows: list[dict] = []
        for row in frame.iter_rows(named=True):
            ref = str(row["customer_external_ref"]).strip()
            meter_id = customer_refs.get(ref)
            if not meter_id:
                skipped += 1
                continue
            ts = row["timestamp"]
            if ts is None:
                skipped += 1
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "meter_id": meter_id,
                    "timestamp": ts,
                    "consumption_kwh": float(row["consumption_kwh"]),
                    "voltage": float(row["voltage"]) if row.get("voltage") not in (None, "") else None,
                    "current": None,
                    "power_factor": (
                        float(row["power_factor"]) if row.get("power_factor") not in (None, "") else None
                    ),
                    "reading_quality": str(row.get("reading_quality") or "good"),
                    "source": str(row.get("source") or "ami"),
                }
            )
            if len(rows) >= READINGS_CHUNK:
                inserted += self._upsert_meter_readings(session, rows)
                rows = []
        if rows:
            inserted += self._upsert_meter_readings(session, rows)
        session.flush()
        return {"inserted_or_updated": inserted, "skipped": skipped, "rows_in_csv": frame.height}

    @staticmethod
    def _upsert_meter_readings(session: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = pg_insert(MeterReading).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["meter_id", "timestamp"],
            set_={
                "consumption_kwh": stmt.excluded.consumption_kwh,
                "voltage": stmt.excluded.voltage,
                "power_factor": stmt.excluded.power_factor,
                "reading_quality": stmt.excluded.reading_quality,
                "source": stmt.excluded.source,
            },
        )
        session.execute(stmt)
        return len(rows)

    def ingest_asset_energy_readings(
        self, session: Session, asset_external_ids: dict[str, str]
    ) -> dict:
        path = self.optional_csv(ASSET_ENERGY_FILE)
        if path is None:
            return {"skipped": True}

        frame = pl.read_csv(path)
        _require_columns(
            frame,
            ("asset_external_id", "timestamp", "energy_input_kwh"),
            ASSET_ENERGY_FILE,
        )
        frame = _parse_timestamps(frame)

        inserted = skipped = 0
        rows: list[dict] = []
        for row in frame.iter_rows(named=True):
            ext = str(row["asset_external_id"]).strip()
            asset_id = asset_external_ids.get(ext)
            if not asset_id:
                skipped += 1
                continue
            ts = row["timestamp"]
            if ts is None:
                skipped += 1
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "asset_id": asset_id,
                    "timestamp": ts,
                    "energy_input_kwh": float(row["energy_input_kwh"]),
                    "energy_output_kwh": (
                        float(row["energy_output_kwh"])
                        if row.get("energy_output_kwh") not in (None, "")
                        else None
                    ),
                    "reading_quality": str(row.get("reading_quality") or "good"),
                    "source": str(row.get("source") or "scada"),
                }
            )
            if len(rows) >= READINGS_CHUNK:
                inserted += self._upsert_asset_energy(session, rows)
                rows = []
        if rows:
            inserted += self._upsert_asset_energy(session, rows)
        session.flush()
        return {"inserted_or_updated": inserted, "skipped": skipped, "rows_in_csv": frame.height}

    @staticmethod
    def _upsert_asset_energy(session: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = pg_insert(AssetEnergyReading).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "timestamp"],
            set_={
                "energy_input_kwh": stmt.excluded.energy_input_kwh,
                "energy_output_kwh": stmt.excluded.energy_output_kwh,
                "reading_quality": stmt.excluded.reading_quality,
                "source": stmt.excluded.source,
            },
        )
        session.execute(stmt)
        return len(rows)

    def ingest_technical_loss_estimates(
        self, session: Session, asset_external_ids: dict[str, str]
    ) -> dict:
        path = self.optional_csv(TECHNICAL_LOSS_FILE)
        if path is None:
            return {"skipped": True}

        frame = pl.read_csv(path)
        _require_columns(
            frame,
            ("asset_external_id", "timestamp", "estimated_technical_loss_kwh"),
            TECHNICAL_LOSS_FILE,
        )
        frame = _parse_timestamps(frame)

        inserted = skipped = 0
        rows: list[dict] = []
        for row in frame.iter_rows(named=True):
            ext = str(row["asset_external_id"]).strip()
            asset_id = asset_external_ids.get(ext)
            if not asset_id:
                skipped += 1
                continue
            ts = row["timestamp"]
            if ts is None:
                skipped += 1
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "asset_id": asset_id,
                    "timestamp": ts,
                    "estimated_technical_loss_kwh": float(row["estimated_technical_loss_kwh"]),
                    "method": str(row.get("method") or "loss_factor"),
                    "confidence": (
                        float(row["confidence"]) if row.get("confidence") not in (None, "") else 0.8
                    ),
                    "model_version": str(row.get("model_version") or "tech-loss-v1"),
                }
            )
            if len(rows) >= READINGS_CHUNK:
                inserted += self._upsert_technical_loss(session, rows)
                rows = []
        if rows:
            inserted += self._upsert_technical_loss(session, rows)
        session.flush()
        return {"inserted_or_updated": inserted, "skipped": skipped, "rows_in_csv": frame.height}

    @staticmethod
    def _upsert_technical_loss(session: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = pg_insert(TechnicalLossEstimate).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "timestamp"],
            set_={
                "estimated_technical_loss_kwh": stmt.excluded.estimated_technical_loss_kwh,
                "method": stmt.excluded.method,
                "confidence": stmt.excluded.confidence,
                "model_version": stmt.excluded.model_version,
            },
        )
        session.execute(stmt)
        return len(rows)

    def run_all(self, session: Session) -> dict:
        """Ingest operators → regions → grid → customers → readings → asset energy."""
        if not self.root.is_dir():
            raise FileNotFoundError(
                f"Production ingest directory not found: {self.root}. "
                "Create data/raw/production/ and add CSVs (see docs/ingest-spec.md)."
            )

        operators = self.ingest_operators(session)
        operator_ids = operators["ids_by_name"]
        regions = self.ingest_regions(session, operator_ids)
        grid = self.ingest_grid_assets(session, operator_ids)
        customers = self.ingest_customers(
            session,
            operator_ids,
            grid["external_ids"],
            regions.get("codes", {}),
        )
        readings = self.ingest_meter_readings(session, customers["external_refs"])
        asset_energy = self.ingest_asset_energy_readings(session, grid["external_ids"])
        technical_loss = self.ingest_technical_loss_estimates(session, grid["external_ids"])

        return {
            "operators": {k: v for k, v in operators.items() if k != "ids_by_name"},
            "regions": {k: v for k, v in regions.items() if k != "codes"},
            "grid_assets": {k: v for k, v in grid.items() if k != "external_ids"},
            "customers": {k: v for k, v in customers.items() if k != "external_refs"},
            "meter_readings": readings,
            "asset_energy_readings": asset_energy,
            "technical_loss_estimates": technical_loss,
            "ingested_at": datetime.now(UTC).isoformat(),
        }
