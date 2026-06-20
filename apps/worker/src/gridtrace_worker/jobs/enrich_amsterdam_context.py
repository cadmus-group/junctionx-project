"""Enrich customers with Amsterdam Woningwaarde + Zonatlas context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from geoalchemy2.shape import to_shape
from gridtrace_api.db.models import AuditLog, Customer
from sqlalchemy import select
from sqlalchemy.orm import Session

from gridtrace_worker.connectors.amsterdam_context import AmsterdamContextConnector
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("enrich_amsterdam_context")


def run(session: Session, seed: int | None = None) -> dict:
    connector = AmsterdamContextConnector()
    connector.fetch()

    customers = session.execute(select(Customer)).scalars().all()
    updated = 0
    solar_count = 0
    for customer in customers:
        if customer.geometry is None:
            continue
        point = to_shape(customer.geometry)
        ctx = connector.classify_customer(float(point.x), float(point.y))
        customer.woningwaarde_category = ctx["woningwaarde_category"]
        customer.solar_potential_flag = bool(ctx["solar_potential_flag"])
        if customer.solar_potential_flag:
            solar_count += 1
        meta = dict(customer.metadata_json or {})
        if ctx.get("zonatlas_label"):
            meta["zonatlas_label"] = ctx["zonatlas_label"]
        customer.metadata_json = meta
        updated += 1

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="enrich_amsterdam_context",
            entity_type="connector",
            entity_id=connector.name,
            payload_json={
                "updated_customers": updated,
                "solar_flagged": solar_count,
                "enriched_at": datetime.now(UTC).isoformat(),
            },
        )
    )

    log_event(
        logger,
        "amsterdam_context_enriched",
        updated=updated,
        solar_flagged=solar_count,
    )
    return {"updated_customers": updated, "solar_flagged": solar_count}
