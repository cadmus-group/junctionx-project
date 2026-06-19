"""Context ingestion job (offline).

Reads local context fixtures via the filesystem connector and records source
freshness into ``audit_logs``. This is intentionally lightweight: it demonstrates
the connector + freshness-tracking contract without any live external API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from gridtrace_api.db.models import AuditLog
from sqlalchemy.orm import Session

from gridtrace_worker.connectors import FilesystemConnector
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("ingest_context")


def _default_context_root() -> Path:
    # apps/worker/src/gridtrace_worker/jobs/ingest_context.py -> repo root / data / fixtures
    return Path(__file__).resolve().parents[5] / "data" / "fixtures"


def run(session: Session, seed: int | None = None, root: str | None = None) -> dict:
    context_root = Path(root) if root else _default_context_root()
    connector = FilesystemConnector(context_root)
    result = connector.fetch()

    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor="worker",
            action="ingest_context",
            entity_type="connector",
            entity_id=connector.name,
            payload_json={
                "freshness": result.freshness.to_dict(),
                "ingested_at": datetime.now(UTC).isoformat(),
            },
        )
    )

    log_event(
        logger,
        "context_ingested",
        connector=connector.name,
        records=len(result.records),
        root=str(context_root),
    )
    return {
        "connector": connector.name,
        "records": len(result.records),
        "freshness": result.freshness.to_dict(),
    }
