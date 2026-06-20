from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridtrace_worker.services.dutch_energy_ingest import (
    DutchEnergySpatialIngestion,
    list_stedin_csv_paths,
    resolve_dutch_energy_source,
)

FIXTURE = Path(__file__).parent / "fixtures" / "stedin_sample.tsv"


def test_resolve_source_prefers_stedin_when_present(tmp_path: Path):
    stedin_dir = tmp_path / "stedin"
    stedin_dir.mkdir()
    (stedin_dir / "stedin_kleinverbruik_2024.csv").write_text("x", encoding="utf-8")

    assert resolve_dutch_energy_source(data_raw_path=tmp_path, explicit=None) == "stedin"


def test_process_stedin_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "stedin" / "stedin_kleinverbruik_2024.csv"
    dest.parent.mkdir(parents=True)
    dest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("DATA_RAW_PATH", str(tmp_path))
    from gridtrace_api.config import get_settings

    get_settings.cache_clear()

    ingest = DutchEnergySpatialIngestion(source="stedin")
    frame = ingest.process_with_polars()

    assert ingest.source == "stedin"
    assert frame.height >= 2
    row = frame.filter(pl.col("zipcode") == "1231AC").to_dicts()[0]
    assert row["baseline_annual_kwh"] == pytest.approx(2525.0, rel=1e-3)
    assert row["street_smartmeter_perc"] == pytest.approx(88.24, rel=1e-3)
    assert row["has_solar_potential"] is True


def test_stedin_zipcode_weights_use_rotterdam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "stedin" / "stedin_kleinverbruik_2024.csv"
    dest.parent.mkdir(parents=True)
    dest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("DATA_RAW_PATH", str(tmp_path))
    from gridtrace_api.config import get_settings

    get_settings.cache_clear()

    ingest = DutchEnergySpatialIngestion(source="stedin")
    weights = ingest.zipcode_weights()
    zipcodes = {zc for zc, _ in weights}
    assert "1231AC" in zipcodes
    assert "1115AC" not in zipcodes


def test_list_stedin_csv_paths_from_repo_raw():
    repo_raw = Path(__file__).resolve().parents[3] / "data" / "raw"
    paths = list_stedin_csv_paths(repo_raw)
    if paths:
        assert all("stedin_kleinverbruik_" in path.name for path in paths)
