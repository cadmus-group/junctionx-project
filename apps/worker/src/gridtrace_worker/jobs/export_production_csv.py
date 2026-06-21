"""Export deterministic demo data as production CSV files."""

from __future__ import annotations

from gridtrace_worker.services.export_production_csv import export_demo_csvs


def run(seed: int, *, data_dir: str | None = None) -> dict:
    return export_demo_csvs(seed, data_dir)
