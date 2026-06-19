"""Map a trained bundle + feature frame to risk scores via the domain formula.

The supervised probability and anomaly score come from the trained models; grid,
peer, and spatial components are normalized features. The 0-100 composite and tier
come from ``gridtrace_domain`` (never re-implemented here), matching the worker.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from gridtrace_domain import RiskComponents, risk_score, risk_tier_for_score

from gridtrace_ml.training import ModelBundle

GRID_RATIO_REF = 0.12
PEER_DEV_REF = 0.70
SPATIAL_REF = 0.50


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0)


def predict_frame(bundle: ModelBundle, frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    X = out[bundle.feature_columns].to_numpy(dtype=float)

    if hasattr(bundle.classifier, "predict_proba"):
        proba = bundle.classifier.predict_proba(X)[:, 1]
    else:  # pragma: no cover
        proba = _clip01(bundle.classifier.predict(X).astype(float))

    raw = -bundle.anomaly.score_samples(X)
    span = max(bundle.anomaly_score_max - bundle.anomaly_score_min, 1e-9)
    anomaly = _clip01((raw - bundle.anomaly_score_min) / span)
    # A flatlined meter is always a maximal anomaly.
    anomaly = np.maximum(anomaly, out["flatline"].to_numpy(dtype=float))

    grid = _clip01(out["grid_unexplained_ratio"].to_numpy(dtype=float) / GRID_RATIO_REF)
    peer = _clip01(np.maximum(0.0, out["peer_deviation"].to_numpy(dtype=float)) / PEER_DEV_REF)
    spatial = _clip01(out["spatial_neighborhood_risk"].to_numpy(dtype=float) / SPATIAL_REF)

    scores = []
    tiers = []
    for i in range(len(out)):
        comp = RiskComponents(
            supervised_probability=float(_clip01(np.array([proba[i]]))[0]),
            anomaly_score=float(anomaly[i]),
            grid_imbalance_score=float(grid[i]),
            peer_score=float(peer[i]),
            spatial_score=float(spatial[i]),
        )
        s = risk_score(comp)
        scores.append(s)
        tiers.append(risk_tier_for_score(s))

    out["supervised_probability"] = proba
    out["anomaly_score"] = anomaly
    out["grid_imbalance_score"] = grid
    out["peer_score"] = peer
    out["spatial_score"] = spatial
    out["risk_score"] = scores
    out["risk_tier"] = tiers
    return out
