"""Ingest customers from ``data/raw/production/customers.csv``."""

from __future__ import annotations

import uuid

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import ProductionIngest

logger = get_logger("ingest_customers")


def run(session: Session, data_dir: str | None = None) -> dict:
    ingest = ProductionIngest(data_dir)
    operators = ingest.ingest_operators(session)
    operator_ids = operators["ids_by_name"]
    regions = ingest.ingest_regions(session, operator_ids)
    grid = ingest.ingest_grid_assets(session, operator_ids)
    result = ingest.ingest_customers(
        session,
        operator_ids,
        grid["external_ids"],
        regions.get("codes", {}),
    )
    customer_count = len(result.pop("external_refs"))
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_customers",
            entity_type="connector",
            entity_id="production_csv",
            payload_json={**result, "customer_count": customer_count},
        )
    )
    log_event(logger, "customers_ingested", **result, customer_count=customer_count)
    return {**result, "customer_count": customer_count}
