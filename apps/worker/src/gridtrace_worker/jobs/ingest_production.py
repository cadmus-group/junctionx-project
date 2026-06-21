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
from gridtrace_worker.services.stedin_ingest import has_stedin_files, transform_stedin_to_production

logger = get_logger("ingest_production")


def _prepare_production_csvs(data_dir: str | None) -> dict | None:
    """If Stedin open-data files are present, transform them into production CSVs."""
    if not has_stedin_files(data_dir):
        return None
    summary = transform_stedin_to_production(data_root=data_dir)
    log_event(logger, "stedin_production_csvs_ready", **summary)
    return summary


def run(
    session: Session,
    seed: int,
    *,
    data_dir: str | None = None,
    truncate: bool = True,
    moment_results_path: str | None = None,
) -> dict:
    if truncate:
        refresh_demo.truncate_operational(session)
        log_event(logger, "production_truncate_complete")

    stedin = _prepare_production_csvs(data_dir)
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
    scoring = score_entities.run(session, seed, moment_results_path=moment_results_path)

    summary = {
        "stedin_transform": stedin,
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
