"""Full production CSV ingest + feature/scoring pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.jobs import (
    build_features,
    enrich_amsterdam_context,
    ingest_dutch_energy,
    poll_ned,
    refresh_demo,
    score_entities,
    sync_olap,
)
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.services.production_ingest import ProductionIngest

logger = get_logger("ingest_production")


def run(
    session: Session,
    seed: int,
    *,
    data_dir: str | None = None,
    truncate: bool = True,
) -> dict:
    if truncate:
        refresh_demo.truncate_operational(session)
        log_event(logger, "production_truncate_complete")

    ingest = ProductionIngest(data_dir)
    csv_summary = ingest.run_all(session)

    from gridtrace_api.modules.auth.bootstrap import ensure_demo_user

    ensure_demo_user(session)

    dutch: dict | None = None
    try:
        dutch = ingest_dutch_energy.run(session, seed)
    except FileNotFoundError as exc:
        log_event(logger, "dutch_energy_skipped", reason=str(exc))
        dutch = {"skipped": str(exc)}

    enrich_amsterdam_context.run(session, seed)
    poll_ned.run(session, seed)
    sync_olap.run(session, seed)
    features = build_features.run(session, seed)
    scoring = score_entities.run(session, seed)

    summary = {
        "csv": csv_summary,
        "dutch_energy": dutch,
        "features": features,
        "scoring": scoring,
    }

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_production",
            entity_type="pipeline",
            entity_id="production_csv",
            payload_json={
                "customers": csv_summary.get("customers"),
                "meter_readings": csv_summary.get("meter_readings"),
                "seed": seed,
                "ingested_at": datetime.now(UTC).isoformat(),
            },
        )
    )
    log_event(logger, "production_pipeline_complete", seed=seed)
    return summary
