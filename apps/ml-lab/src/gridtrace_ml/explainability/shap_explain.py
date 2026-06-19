"""Explanation generation.

Uses SHAP when available to produce per-customer contributions; otherwise falls
back to a model-derived global importance (so explanations are always generated,
satisfying the demo's transparency requirement).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gridtrace_ml.training import ModelBundle

_LABELS = {
    "baseline_mean_kwh": "Baseline consumption",
    "recent_mean_kwh": "Recent consumption",
    "drop_ratio": "Recent/baseline ratio",
    "trend": "Consumption trend",
    "night_day_ratio": "Night/day ratio",
    "zero_fraction": "Zero-reading fraction",
    "flatline": "Flatlined meter",
    "anomaly_z": "Consumption anomaly (z)",
    "peer_deviation": "Peer deviation",
    "grid_unexplained_ratio": "Grid unexplained-loss ratio",
    "spatial_neighborhood_risk": "Neighborhood risk",
}


def _shap_values(bundle: ModelBundle, X: np.ndarray) -> np.ndarray | None:
    try:
        import shap

        explainer = shap.TreeExplainer(bundle.classifier)
        values = explainer.shap_values(X)
        if isinstance(values, list):  # binary classifier -> [class0, class1]
            values = values[-1]
        return np.asarray(values)
    except Exception:  # pragma: no cover - shap optional / model unsupported
        return None


def global_importances(bundle: ModelBundle, frame: pd.DataFrame) -> dict[str, float]:
    cols = bundle.feature_columns
    X = frame[cols].to_numpy(dtype=float)
    sv = _shap_values(bundle, X)
    if sv is not None:
        mag = np.abs(sv).mean(axis=0)
    elif hasattr(bundle.classifier, "feature_importances_"):
        mag = np.asarray(bundle.classifier.feature_importances_, dtype=float)
    else:  # pragma: no cover
        mag = np.ones(len(cols))
    total = float(mag.sum()) or 1.0
    return {c: round(float(m) / total, 6) for c, m in zip(cols, mag, strict=False)}


def explain_customer(
    bundle: ModelBundle, frame: pd.DataFrame, external_ref: str, top_n: int = 5
) -> list[dict]:
    """Top contributing features for one customer, as explanation dicts."""
    cols = bundle.feature_columns
    row = frame.loc[frame["external_ref"] == external_ref]
    if row.empty:
        raise KeyError(external_ref)
    X = row[cols].to_numpy(dtype=float)
    sv = _shap_values(bundle, X)
    if sv is not None:
        contributions = sv[0]
    else:
        gi = global_importances(bundle, frame)
        contributions = np.array([gi[c] for c in cols])

    order = np.argsort(-np.abs(contributions))[:top_n]
    out = []
    for idx in order:
        col = cols[idx]
        val = float(contributions[idx])
        out.append(
            {
                "feature": col,
                "label": _LABELS.get(col, col),
                "contribution": round(val, 6),
                "direction": "increases" if val >= 0 else "decreases",
                "detail": f"Feature value={round(float(X[0][idx]), 4)}",
            }
        )
    return out
