"""Export the deterministic demo dataset as production CSV files.

Writes the same data ``build_demo_dataset`` produces in-memory into
``data/raw/production/*.csv`` so the real CSV ingest pipeline can load it.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import polars as pl

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.jobs.generate_synthetic import DemoDataset, build_demo_dataset
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import PRODUCTION_SUBDIR

logger = get_logger("export_production_csv")

OPERATORS_FILE = "operators.csv"
REGIONS_FILE = "regions.csv"
GRID_ASSETS_FILE = "grid_assets.csv"
CUSTOMERS_FILE = "customers.csv"
METER_READINGS_FILE = "meter_readings.csv"
ASSET_ENERGY_FILE = "asset_energy_readings.csv"
TECHNICAL_LOSS_FILE = "technical_loss_estimates.csv"


def _iso(ts) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.isoformat().replace("+00:00", "Z")


def export_dataset(dataset: DemoDataset, output_root: Path) -> dict:
    """Write ``dataset`` to ``output_root/production/*.csv``."""
    out = output_root / PRODUCTION_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    op_name = dataset.operator["name"]
    neighborhood_codes = [
        r["code"] for r in dataset.regions if r["region_type"] == "neighborhood"
    ]

    pl.DataFrame([dataset.operator]).write_csv(out / OPERATORS_FILE)

    region_rows = [
        {
            "code": r["code"],
            "name": r["name"],
            "region_type": r["region_type"],
            "operator_name": op_name,
            "parent_code": r["parent_code"] or "",
        }
        for r in dataset.regions
    ]
    pl.DataFrame(region_rows).write_csv(out / REGIONS_FILE)

    grid_rows: list[dict] = []
    for f in dataset.feeders:
        grid_rows.append(
            {
                "external_id": f["external_id"],
                "asset_type": "feeder",
                "name": f["name"],
                "operator_name": op_name,
                "lon": f["lon"],
                "lat": f["lat"],
                "parent_external_id": "",
                "voltage_level": f["voltage_level"],
                "capacity_kva": "",
            }
        )
    for tx in dataset.transformers:
        feeder = dataset.feeders[tx.feeder_idx]
        grid_rows.append(
            {
                "external_id": tx.external_id,
                "asset_type": "transformer",
                "name": f"Transformer {tx.external_id}",
                "operator_name": op_name,
                "lon": tx.lon,
                "lat": tx.lat,
                "parent_external_id": feeder["external_id"],
                "voltage_level": tx.voltage_level,
                "capacity_kva": tx.capacity_kva,
            }
        )
    pl.DataFrame(grid_rows).write_csv(out / GRID_ASSETS_FILE)

    customer_rows: list[dict] = []
    for c in dataset.customers:
        tx = dataset.transformers[c.transformer_idx]
        feeder = dataset.feeders[c.feeder_idx]
        customer_rows.append(
            {
                "external_ref": c.external_ref,
                "customer_type": c.customer_type,
                "operator_name": op_name,
                "lon": c.lon,
                "lat": c.lat,
                "transformer_external_id": tx.external_id,
                "feeder_external_id": feeder["external_id"],
                "region_code": neighborhood_codes[c.neighborhood_idx],
                "zipcode": "",
                "building_type": "apartment" if c.customer_type == "residential" else "office",
                "tariff_type": "single",
                "incident": c.incident or "",
                "is_ntl": str(bool(c.is_ntl)).lower(),
            }
        )
    pl.DataFrame(customer_rows).write_csv(out / CUSTOMERS_FILE)

    meter_rows: list[dict] = []
    for c in dataset.customers:
        for i, ts in enumerate(dataset.timestamps):
            meter_rows.append(
                {
                    "customer_external_ref": c.external_ref,
                    "timestamp": _iso(ts),
                    "consumption_kwh": round(float(c.meter_kwh[i]), 6),
                    "voltage": 230,
                    "power_factor": "",
                    "reading_quality": "good",
                    "source": "ami",
                }
            )
    pl.DataFrame(meter_rows).write_csv(out / METER_READINGS_FILE)

    asset_energy_rows: list[dict] = []
    tech_loss_rows: list[dict] = []
    for tx in dataset.transformers:
        for i, ts in enumerate(dataset.timestamps):
            asset_energy_rows.append(
                {
                    "asset_external_id": tx.external_id,
                    "timestamp": _iso(ts),
                    "energy_input_kwh": round(float(tx.input_kwh[i]), 6),
                    "energy_output_kwh": "",
                    "reading_quality": "good",
                    "source": "scada",
                }
            )
            tech_loss_rows.append(
                {
                    "asset_external_id": tx.external_id,
                    "timestamp": _iso(ts),
                    "estimated_technical_loss_kwh": round(float(tx.technical_kwh[i]), 6),
                    "method": "loss_factor",
                    "confidence": 0.8,
                }
            )
    pl.DataFrame(asset_energy_rows).write_csv(out / ASSET_ENERGY_FILE)
    pl.DataFrame(tech_loss_rows).write_csv(out / TECHNICAL_LOSS_FILE)

    summary = {
        "output_dir": str(out),
        "seed": dataset.seed,
        "operators": 1,
        "regions": len(dataset.regions),
        "grid_assets": len(grid_rows),
        "customers": len(customer_rows),
        "meter_readings": len(meter_rows),
        "asset_energy_readings": len(asset_energy_rows),
        "technical_loss_estimates": len(tech_loss_rows),
        "showcase": dataset.showcase,
    }
    log_event(logger, "production_csv_exported", **{k: v for k, v in summary.items() if k != "showcase"})
    return summary


def export_demo_csvs(seed: int, data_root: str | Path | None = None) -> dict:
    """Build demo dataset and write production CSV files."""
    cfg = get_worker_config()
    base = Path(data_root) if data_root is not None else Path(cfg.data_raw_path)
    dataset = build_demo_dataset(seed)
    return export_dataset(dataset, base)
