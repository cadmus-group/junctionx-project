"""Ingest operators from ``data/raw/production/operators.csv``."""

from __future__ import annotations

import uuid

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import ProductionIngest

logger = get_logger("ingest_operators")


def run(session: Session, data_dir: str | None = None) -> dict:
    ingest = ProductionIngest(data_dir)
    result = ingest.ingest_operators(session)
    operator_ids = result.pop("ids_by_name")
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_operators",
            entity_type="connector",
            entity_id="production_csv",
            payload_json={**result, "operator_count": len(operator_ids)},
        )
    )
    log_event(logger, "operators_ingested", **result)
    return {**result, "operator_count": len(operator_ids)}
