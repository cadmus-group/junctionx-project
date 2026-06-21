"""Ingest grid assets from ``data/raw/production/grid_assets.csv``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import ProductionIngest

logger = get_logger("ingest_grid")


def run(session: Session, data_dir: str | None = None) -> dict:
    ingest = ProductionIngest(data_dir)
    operators = ingest.ingest_operators(session)
    operator_ids = operators["ids_by_name"]
    result = ingest.ingest_grid_assets(session, operator_ids)
    asset_count = len(result.pop("external_ids"))
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_grid",
            entity_type="connector",
            entity_id="production_csv",
            payload_json={**result, "asset_count": asset_count},
        )
    )
    log_event(logger, "grid_ingested", **result, asset_count=asset_count)
    return {**result, "asset_count": asset_count}
