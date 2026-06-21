"""Periodic scheduling for worker jobs.

APScheduler is the deterministic default and runs in-process with no external
dependency. ARQ (Redis-backed) is only selected when ``REDIS_URL`` is configured;
since the demo has no Redis by default, APScheduler is what actually runs.
"""

from __future__ import annotations

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.db import session_scope
from gridtrace_worker.jobs import (
    build_features,
    build_hotspots,
    enrich_amsterdam_context,
    ingest_context,
    poll_ned,
    score_entities,
    sync_olap,
)
from gridtrace_worker.jobs.score_entities import moment_results_path_for_scoring
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("scheduler")


def _refresh_scores() -> None:
    """Recompute features, scores, and hotspots from current readings."""
    from pathlib import Path

    cfg = get_worker_config()
    log_event(
        logger,
        "refresh_scores_start",
        moment_enabled=cfg.moment_active,
        model_version=cfg.moment_model_name if cfg.moment_active else None,
    )
    moment_path, exported_path = moment_results_path_for_scoring()
    try:
        with session_scope() as session:
            poll_ned.run(session)
            sync_olap.run(session)
            build_features.run(session)
            score_entities.run(session, moment_results_path=moment_path)
            build_hotspots.run(session)
    finally:
        if exported_path:
            Path(exported_path).unlink(missing_ok=True)
    log_event(logger, "refresh_scores_complete")


def _ingest() -> None:
    with session_scope() as session:
        ingest_context.run(session)
        enrich_amsterdam_context.run(session)


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
