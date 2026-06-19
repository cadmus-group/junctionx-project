"""Periodic scheduling for worker jobs.

APScheduler is the deterministic default and runs in-process with no external
dependency. ARQ (Redis-backed) is only selected when ``REDIS_URL`` is configured;
since the demo has no Redis by default, APScheduler is what actually runs.
"""

from __future__ import annotations

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.db import session_scope
from gridtrace_worker.jobs import build_features, build_hotspots, ingest_context, score_entities
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("scheduler")


def _refresh_scores() -> None:
    """Recompute features, scores, and hotspots from current readings."""
    with session_scope() as session:
        build_features.run(session)
        score_entities.run(session)
        build_hotspots.run(session)


def _ingest() -> None:
    with session_scope() as session:
        ingest_context.run(session)


def build_apscheduler(score_interval_minutes: int = 30, ingest_interval_minutes: int = 60):
    """Construct a BlockingScheduler with the worker's recurring jobs."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _refresh_scores,
        "interval",
        minutes=score_interval_minutes,
        id="refresh_scores",
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        _ingest,
        "interval",
        minutes=ingest_interval_minutes,
        id="ingest_context",
        coalesce=True,
        max_instances=1,
    )
    return scheduler


def run_scheduler() -> None:
    cfg = get_worker_config()
    if cfg.use_arq:
        log_event(
            logger,
            "scheduler_backend_selected",
            backend="arq",
            note="REDIS_URL set; enqueue jobs via ARQ in a production deployment.",
        )
    log_event(logger, "scheduler_starting", backend="apscheduler")
    scheduler = build_apscheduler()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log_event(logger, "scheduler_stopped")
