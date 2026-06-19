"""Persist and load model artifacts.

Layout under ``artifacts/<model_version>/``:
    model.joblib            serialized ModelBundle
    metadata.json           sidecar: versions, algorithm, metrics, feature columns
    predictions.parquet     analytical store of scored rows
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from gridtrace_ml import FEATURE_VERSION
from gridtrace_ml.training import ModelBundle

DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts"


def save_artifact(
    bundle: ModelBundle,
    metrics: dict,
    predictions: pd.DataFrame,
    model_version: str,
    artifacts_dir: Path | str | None = None,
    notes: str | None = None,
) -> dict:
    import joblib

    base = Path(artifacts_dir) if artifacts_dir else DEFAULT_ARTIFACTS_DIR
    out_dir = base / model_version
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "model.joblib"
    joblib.dump(bundle, model_path)

    predictions_path = out_dir / "predictions.parquet"
    predictions.to_parquet(predictions_path, index=False)

    metadata = {
        "model_version": model_version,
        "feature_version": FEATURE_VERSION,
        "algorithm": bundle.algorithm,
        "feature_columns": bundle.feature_columns,
        "trained_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "training_metadata": bundle.metadata,
        "notes": notes,
        "files": {
            "model": model_path.name,
            "predictions": predictions_path.name,
        },
    }
    metadata_path = out_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str))

    return {**metadata, "artifact_dir": str(out_dir)}


def load_bundle(model_version: str, artifacts_dir: Path | str | None = None):
    import joblib

    base = Path(artifacts_dir) if artifacts_dir else DEFAULT_ARTIFACTS_DIR
    out_dir = base / model_version
    bundle = joblib.load(out_dir / "model.joblib")
    metadata = json.loads((out_dir / "metadata.json").read_text())
    return bundle, metadata
