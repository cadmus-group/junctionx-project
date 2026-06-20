"""CLI dispatcher for the GridTrace worker.

Usage::

    python -m gridtrace_worker.main <command> [--seed N]

Commands:
    seed              Full pipeline: generate-synthetic -> build-features -> score-entities
    refresh-demo      Truncate operational data, re-seed, verify showcase invariants
    ingest-context    Ingest local offline context fixtures (records source freshness)
    poll-ned          Poll NED macro baseline -> ned_grid_status.parquet
    sync-olap         Export meter readings + DuckDB feature analytics to Parquet
    enrich-amsterdam  Apply Woningwaarde + Zonatlas context to customers
    generate-synthetic  Generate + persist the deterministic synthetic dataset
    build-features    Build feature_snapshots from readings
    score-entities    Score customers + transformers and publish atomically
    score-moment      Run MOMENT inference only (debug; prints summary JSON)
    build-hotspots    Aggregate current risk into neighborhood hotspots
    scheduler         Run the APScheduler loop (ARQ only when REDIS_URL is set)
"""

from __future__ import annotations

import argparse
import json
import sys

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.db import session_scope
from gridtrace_worker.jobs import (
    build_features,
    build_hotspots,
    enrich_amsterdam_context,
    generate_synthetic,
    ingest_context,
    poll_ned,
    refresh_demo,
    score_entities,
    sync_olap,
)
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("main")


def _seed_value(args: argparse.Namespace) -> int:
    if args.seed is not None:
        return int(args.seed)
    return get_worker_config().demo_seed


def _run_seed_pipeline(seed: int) -> dict:
    """generate-synthetic -> enrich -> sync OLAP -> build-features -> score-entities."""
    with session_scope() as session:
        gen = generate_synthetic.run(session, seed)
        enrich_amsterdam_context.run(session, seed)
        poll_ned.run(session, seed)
        sync_olap.run(session, seed)
        feat = build_features.run(session, seed)
        scored = score_entities.run(session, seed)
    return {"generate": gen.get("showcase"), "features": feat, "scoring": scored}


def cmd_generate(args: argparse.Namespace) -> int:
    seed = _seed_value(args)
    with session_scope() as session:
        result = generate_synthetic.run(session, seed)
    log_event(logger, "command_complete", command="generate-synthetic", seed=seed)
    print(json.dumps(result.get("showcase", {}), indent=2, default=str))
    return 0


def cmd_build_features(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = build_features.run(session, _seed_value(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = score_entities.run(session, _seed_value(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_build_hotspots(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = build_hotspots.run(session, _seed_value(args))
    print(json.dumps({"regions": result["regions"]}, indent=2, default=str))
    return 0


def cmd_ingest_context(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = ingest_context.run(session, _seed_value(args), root=args.root)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_poll_ned(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = poll_ned.run(session, _seed_value(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_sync_olap(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = sync_olap.run(session, _seed_value(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_enrich_amsterdam(args: argparse.Namespace) -> int:
    with session_scope() as session:
        result = enrich_amsterdam_context.run(session, _seed_value(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    seed = _seed_value(args)
    summary = _run_seed_pipeline(seed)
    log_event(logger, "command_complete", command="seed", seed=seed)
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_refresh_demo(args: argparse.Namespace) -> int:
    seed = _seed_value(args)
    with session_scope() as session:
        refresh_demo.truncate_operational(session)
    summary = _run_seed_pipeline(seed)
    with session_scope() as session:
        ok, checks = refresh_demo.verify(session)

    print("=" * 64)
    print("GridTrace demo refresh verification")
    print("=" * 64)
    print(
        json.dumps(
            {"seed": seed, "passed": ok, "pipeline": summary, "checks": checks},
            indent=2,
            default=str,
        )
    )
    print("=" * 64)
    if not ok:
        print("VERIFICATION FAILED: showcase invariants not met.", file=sys.stderr)
        return 1
    print("VERIFICATION PASSED")
    return 0


def cmd_score_moment(args: argparse.Namespace) -> int:
    from gridtrace_worker.ml import ml_deps_available

    cfg = get_worker_config()
    if not cfg.moment_active:
        print(
            json.dumps(
                {
                    "error": "MOMENT not active",
                    "moment_enabled": cfg.moment_enabled,
                    "ml_deps_available": ml_deps_available(),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    from gridtrace_worker.ml.moment_pipeline import MOMENTInferencePipeline

    pipeline = MOMENTInferencePipeline(cfg)
    results = pipeline.infer(cfg.database_url)
    summary = {
        "scored_customers": len(results),
        "model": cfg.moment_model_name,
        "context_length": cfg.moment_context_length,
        "top_anomalies": sorted(
            [
                {
                    "customer_id": r.customer_id,
                    "anomaly_score": round(r.anomaly_score, 4),
                    "reconstruction_mse": round(r.reconstruction_mse, 6),
                }
                for r in results.values()
            ],
            key=lambda x: x["anomaly_score"],
            reverse=True,
        )[:10],
    }
    log_event(logger, "command_complete", command="score-moment", scored=len(results))
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_scheduler(args: argparse.Namespace) -> int:
    from gridtrace_worker.scheduler import run_scheduler

    run_scheduler()
    return 0


_COMMANDS = {
    "seed": cmd_seed,
    "refresh-demo": cmd_refresh_demo,
    "ingest-context": cmd_ingest_context,
    "poll-ned": cmd_poll_ned,
    "sync-olap": cmd_sync_olap,
    "enrich-amsterdam": cmd_enrich_amsterdam,
    "generate-synthetic": cmd_generate,
    "build-features": cmd_build_features,
    "score-entities": cmd_score,
    "score-moment": cmd_score_moment,
    "build-hotspots": cmd_build_hotspots,
    "scheduler": cmd_scheduler,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gridtrace_worker", description=__doc__)
    parser.add_argument("command", choices=sorted(_COMMANDS), help="Subcommand to run")
    parser.add_argument("--seed", type=int, default=None, help="Override DEMO_SEED")
    parser.add_argument("--root", type=str, default=None, help="Context fixtures root (ingest-context)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
