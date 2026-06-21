"""Tests for production CSV ingest."""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path

import polars as pl
import pytest
from gridtrace_worker.services.production_ingest import (
    CUSTOMERS_FILE,
    GRID_ASSETS_FILE,
    METER_READINGS_FILE,
    OPERATORS_FILE,
    _customer_metadata,
    _require_columns,
)

FIXTURES = Path(__file__).parent / "fixtures" / "production"


def test_require_columns_raises_on_missing():
    frame = pl.DataFrame({"name": ["x"]})
    with pytest.raises(ValueError, match="missing required columns"):
        _require_columns(frame, ("name", "country_code"), "operators.csv")


def test_customer_metadata_from_csv_row():
    meta = _customer_metadata(
        {"incident": "partial_bypass", "is_ntl": "true", "external_ref": "C-1"}
    )
    assert meta == {
        "source": "production_csv",
        "incident": "partial_bypass",
        "is_ntl": True,
    }


def test_customer_metadata_omits_empty_optional_fields():
    assert _customer_metadata({}) == {"source": "production_csv"}


def test_fixture_csvs_have_required_columns():
    # FIXTURES is .../fixtures/production — ProductionIngest expects .../production subdir
    root = FIXTURES
    ops = pl.read_csv(root / OPERATORS_FILE)
    _require_columns(ops, ("name", "country_code"), OPERATORS_FILE)
    grid = pl.read_csv(root / GRID_ASSETS_FILE)
    _require_columns(
        grid,
        ("external_id", "asset_type", "name", "operator_name", "lon", "lat"),
        GRID_ASSETS_FILE,
    )
    cust = pl.read_csv(root / CUSTOMERS_FILE)
    _require_columns(
        cust,
        ("external_ref", "customer_type", "operator_name", "lon", "lat"),
        CUSTOMERS_FILE,
    )
    readings = pl.read_csv(root / METER_READINGS_FILE)
    _require_columns(
        readings,
        ("customer_external_ref", "timestamp", "consumption_kwh"),
        METER_READINGS_FILE,
    )


@pytest.fixture
def production_fixture_dir(tmp_path: Path) -> Path:
    dest = tmp_path / "production"
    shutil.copytree(FIXTURES, dest)
    return tmp_path


@pytest.mark.integration
def test_production_ingest_run_all(production_fixture_dir: Path):
    """End-to-end ingest against Postgres (gridtrace_test). Skips if unavailable."""
    pytest.importorskip("asyncpg")
    from gridtrace_worker.services.production_ingest import ProductionIngest
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://gridtrace:gridtrace@localhost:5432/gridtrace_test",
    )
    sync_url = url.replace("+asyncpg", "+psycopg")
    engine = create_engine(sync_url, future=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL test database not reachable")

    # Ensure unique indexes exist (migration 0005)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        for stmt in (
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_operator_external_ref
            ON customers (operator_id, external_ref)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_grid_assets_operator_external_id
            ON grid_assets (operator_id, external_id)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_meter_readings_meter_ts
            ON meter_readings (meter_id, timestamp)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_asset_energy_readings_asset_ts
            ON asset_energy_readings (asset_id, timestamp)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_technical_loss_estimates_asset_ts
            ON technical_loss_estimates (asset_id, timestamp)
            """,
        ):
            # tables may not exist yet on an empty DB
            with contextlib.suppress(Exception):
                conn.execute(text(stmt))

    Session = sessionmaker(bind=engine)
    ingest = ProductionIngest(data_root=production_fixture_dir)

    with Session() as session:
        try:
            summary = ingest.run_all(session)
            session.commit()
        except Exception as exc:
            session.rollback()
            if "does not exist" in str(exc).lower():
                pytest.skip("Schema not migrated on test database")
            raise

    assert summary["customers"]["inserted"] + summary["customers"]["updated"] >= 2
    assert summary["meter_readings"]["inserted_or_updated"] >= 4

    # Idempotent re-run
    with Session() as session:
        summary2 = ingest.run_all(session)
        session.commit()
    assert summary2["customers"]["updated"] >= 2
    assert summary2["meter_readings"]["inserted_or_updated"] >= 4

    engine.dispose()
