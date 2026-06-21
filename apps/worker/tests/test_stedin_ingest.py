from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from gridtrace_worker.services.stedin_ingest import (
    _postcode_to_lonlat,
    has_stedin_files,
    load_stedin_elk,
)


def test_postcode_geocoding_in_netherlands() -> None:
    lon, lat = _postcode_to_lonlat("2719TB", "ZOETERMEER")
    assert 3.0 < lon < 7.5
    assert 50.5 < lat < 53.5
    lon2, lat2 = _postcode_to_lonlat("3065SC", "ROTTERDAM")
    assert 4.0 < lon2 < 5.0
    assert 51.7 < lat2 < 52.2


@pytest.fixture
def stedin_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "data" / "raw"
    if not has_stedin_files(root):
        pytest.skip("Stedin CSV files not present under data/raw/Stedin/")
    return root


def test_has_stedin_files(stedin_root: Path) -> None:
    assert has_stedin_files(stedin_root)


def test_load_stedin_elk_filters_electricity(stedin_root: Path) -> None:
    frame = load_stedin_elk(stedin_root / "Stedin")
    assert frame.height > 0
    assert frame.select(pl.col("sja_kwh").min()).item() > 0
