"""Ingest meter readings from ``data/raw/production/meter_readings.csv``."""

from __future__ import annotations

import uuid

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import ProductionIngest

logger = get_logger("ingest_readings")


def run(session: Session, data_dir: str | None = None) -> dict:
    ingest = ProductionIngest(data_dir)
    operators = ingest.ingest_operators(session)
    operator_ids = operators["ids_by_name"]
    regions = ingest.ingest_regions(session, operator_ids)
    grid = ingest.ingest_grid_assets(session, operator_ids)
    customers = ingest.ingest_customers(
        session,
        operator_ids,
        grid["external_ids"],
        regions.get("codes", {}),
    )
    result = ingest.ingest_meter_readings(session, customers["external_refs"])
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_readings",
            entity_type="connector",
            entity_id="production_csv",
            payload_json=result,
        )
    )
    log_event(logger, "readings_ingested", **result)
    return result
