"""Ingest Dutch DSO street baselines (Stedin or Liander) into customer spatial context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.dutch_energy_ingest import DutchEnergySpatialIngestion

logger = get_logger("ingest_dutch_energy")


def run(
    session: Session,
    seed: int | None = None,
    csv_path: str | None = None,
    source: str | None = None,
) -> dict:
    from gridtrace_worker.config import get_worker_config

    cfg = get_worker_config()
    resolved_seed = cfg.demo_seed if seed is None else seed
    resolved_source = source or cfg.dutch_energy_source
    ingest = DutchEnergySpatialIngestion(csv_path=csv_path, source=resolved_source)
    result = ingest.run(session, resolved_seed)

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_dutch_energy",
            entity_type="connector",
            entity_id=f"{result['source']}_electricity",
            payload_json={
                **result,
                "seed": resolved_seed,
                "ingested_at": datetime.now(UTC).isoformat(),
            },
        )
    )

    log_event(logger, "dutch_energy_ingested", **result, seed=resolved_seed)
    return result
