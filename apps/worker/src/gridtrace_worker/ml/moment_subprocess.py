"""Child-process entrypoint for isolated MOMENT inference."""

from __future__ import annotations

import sys
from pathlib import Path

from gridtrace_worker.config import get_worker_config
from gridtrace_worker.ml.moment_isolated import write_moment_results
from gridtrace_worker.ml.moment_pipeline import MOMENTInferencePipeline


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m gridtrace_worker.ml.moment_subprocess OUTPUT.json", file=sys.stderr)
        return 2

    out_path = Path(args[0])
    cfg = get_worker_config()
    if not cfg.moment_active:
        write_moment_results(out_path, {})
        return 0

    results = MOMENTInferencePipeline(cfg).infer(cfg.database_url)
    write_moment_results(out_path, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
