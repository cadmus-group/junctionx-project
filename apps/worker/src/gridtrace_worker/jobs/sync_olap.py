"""Sync PostgreSQL meter readings to Parquet and run DuckDB feature analytics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from gridtrace_api.db.models import AuditLog, Customer
from sqlalchemy import select
from sqlalchemy.orm import Session

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.olap.duckdb_pipeline import (
    compute_customer_features,
    export_meter_readings,
    parquet_paths,
    persist_feature_parquet,
)

logger = get_logger("sync_olap")


def run(session: Session, seed: int | None = None) -> dict:
    cfg = get_worker_config()
    paths = parquet_paths(cfg.data_processed_path)

    meter_rows = export_meter_readings(session, paths["meter_readings"])
    customers = session.execute(select(Customer)).scalars().all()
    features = compute_customer_features(cfg.data_processed_path, customers)
    feature_rows = persist_feature_parquet(features, paths["customer_features"])

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="sync_olap",
            entity_type="olap",
            entity_id="duckdb",
            payload_json={
                "meter_readings_rows": meter_rows,
                "feature_rows": feature_rows,
                "parquet": {k: str(v) for k, v in paths.items()},
                "synced_at": datetime.now(UTC).isoformat(),
            },
        )
    )

    log_event(
        logger,
        "olap_synced",
        meter_rows=meter_rows,
        feature_rows=feature_rows,
        processed_root=str(cfg.data_processed_path),
    )
    return {
        "meter_readings_rows": meter_rows,
        "feature_rows": feature_rows,
        "parquet": {k: str(v) for k, v in paths.items()},
    }
