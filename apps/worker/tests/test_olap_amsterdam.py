"""Tests for Amsterdam context + DuckDB OLAP helpers."""

from __future__ import annotations

from gridtrace_worker.connectors.amsterdam_context import AmsterdamContextConnector
from gridtrace_worker.connectors.ned import NEDConnector
from gridtrace_worker.olap.duckdb_pipeline import write_ned_parquet


def test_amsterdam_context_classifies_near_woningwaarde_zone():
    connector = AmsterdamContextConnector()
    ctx = connector.classify_customer(4.896, 52.371)
    assert ctx["woningwaarde_category"] in {"A", "B", "C", "D", "E"}


def test_ned_offline_connector_returns_rows():
    connector = NEDConnector(api_key=None)
    result = connector.fetch(hours=6)
    assert len(result.records) == 6
    assert "national_load_mw" in result.records[0]


def test_write_ned_parquet(tmp_path):
    records = [
        {
            "timestamp": "2026-06-20T12:00:00+00:00",
            "national_load_mw": 10000.0,
            "production_mix_solar": 0.4,
            "production_mix_wind": 0.3,
            "grid_status_flag": "normal",
        }
    ]
    out = tmp_path / "ned_grid_status.parquet"
    rows = write_ned_parquet(records, out)
    assert rows == 1
    assert out.is_file()
