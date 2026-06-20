"""Poll NED macro grid baseline and persist to ``ned_grid_status.parquet``."""

from __future__ import annotations

import uuid

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.connectors.ned import NEDConnector
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.olap.duckdb_pipeline import parquet_paths, write_ned_parquet

logger = get_logger("poll_ned")


def run(session: Session, seed: int | None = None, hours: int = 48) -> dict:
    cfg = get_worker_config()
    connector = NEDConnector(api_key=cfg.ned_api_key)
    result = connector.fetch(hours=hours)
    paths = parquet_paths(cfg.data_processed_path)
    rows = write_ned_parquet(result.records, paths["ned_grid_status"])

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="poll_ned",
            entity_type="connector",
            entity_id=connector.name,
            payload_json={
                "freshness": result.freshness.to_dict(),
                "parquet": str(paths["ned_grid_status"]),
                "rows": rows,
            },
        )
    )

    log_event(
        logger,
        "ned_polled",
        rows=rows,
        mode=result.freshness.detail.get("mode", "unknown"),
        parquet=str(paths["ned_grid_status"]),
    )
    return {
        "rows": rows,
        "parquet": str(paths["ned_grid_status"]),
        "freshness": result.freshness.to_dict(),
    }
