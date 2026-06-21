"""Run MOMENT inference in an isolated subprocess.

PyTorch + LightGBM/SHAP in the same process can segfault on macOS after MOMENT
finishes. Spawning a child process loads torch only there; the parent continues
with sklearn/LightGBM for the rest of ``score-entities``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.ml.moment_pipeline import MomentAnomalyResult

logger = get_logger("moment_isolated")


def _deserialize_results(raw: dict[str, dict]) -> dict[str, MomentAnomalyResult]:
    return {
        customer_id: MomentAnomalyResult(
            customer_id=item["customer_id"],
            anomaly_score=float(item["anomaly_score"]),
            reconstruction_mse=float(item["reconstruction_mse"]),
            peak_timestamps=list(item.get("peak_timestamps") or []),
            peak_errors=[float(v) for v in (item.get("peak_errors") or [])],
        )
        for customer_id, item in raw.items()
    }


def run_moment_subprocess() -> dict[str, MomentAnomalyResult]:
    """Spawn MOMENT in a fresh Python process and return scored customers."""
    fd, path = tempfile.mkstemp(prefix="gridtrace-moment-", suffix=".json")
    os.close(fd)
    out_path = Path(path)
    try:
        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[5]
        proc = subprocess.run(
            [sys.executable, "-m", "gridtrace_worker.ml.moment_subprocess", str(out_path)],
            cwd=repo_root,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"MOMENT subprocess exited with code {proc.returncode}")
        if not out_path.is_file():
            raise RuntimeError("MOMENT subprocess did not write results")
        raw = json.loads(out_path.read_text(encoding="utf-8"))
        results = _deserialize_results(raw)
        log_event(logger, "moment_subprocess_complete", scored=len(results))
        return results
    finally:
        out_path.unlink(missing_ok=True)


def write_moment_results(path: Path, results: dict[str, MomentAnomalyResult]) -> None:
    payload = {cid: asdict(result) for cid, result in results.items()}
    path.write_text(json.dumps(payload), encoding="utf-8")
