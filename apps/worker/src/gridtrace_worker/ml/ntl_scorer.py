"""Live supervised + unsupervised NTL scoring on the current feature population.

This wires the "AI model" into the worker's live scoring path that writes
``risk_scores``:

* a **supervised theft / no-theft classifier** (LightGBM when available, otherwise
  scikit-learn ``GradientBoostingClassifier``) trained on the ``is_ntl`` labels
  carried on each customer feature snapshot, producing the ``supervised_probability``
  component (the model's probability of non-technical loss);
* an **IsolationForest** anomaly detector producing the ``anomaly_score`` component;
* per-customer **explanations** via SHAP ``TreeExplainer`` when ``shap`` is installed,
  with a deterministic model-importance fallback otherwise.

The composite 0-100 ``risk_score`` and tier are still produced by
``gridtrace_domain`` (never re-implemented here). If scikit-learn is unavailable or
the label population is too small/degenerate, :func:`score_customers` returns
``None`` and the caller falls back to the deterministic heuristic.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from typing import Any

import numpy as np

# Numeric feature columns fed to the model (stable order — mirrors apps/ml-lab).
FEATURE_COLUMNS: list[str] = [
    "baseline_mean_kwh",
    "recent_mean_kwh",
    "drop_ratio",
    "trend",
    "night_day_ratio",
    "zero_fraction",
    "flatline",
    "anomaly_z",
    "peer_deviation",
    "grid_unexplained_ratio",
    "spatial_neighborhood_risk",
]

_FEATURE_LABELS: dict[str, str] = {
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

# Minimum population requirements for a trustworthy supervised fit.
MIN_ROWS = 40
MIN_POSITIVES = 5
MIN_NEGATIVES = 5


@dataclass
class CustomerMLResult:
    supervised_probability: float
    anomaly_score: float
    explanations: list[dict]


@dataclass
class MLScoring:
    results: dict[str, CustomerMLResult]
    algorithm: str
    metrics: dict[str, Any] = field(default_factory=dict)
    feature_importances: dict[str, float] = field(default_factory=dict)


def ml_available() -> bool:
    """True when scikit-learn (the minimum requirement) is importable."""
    return importlib.util.find_spec("sklearn") is not None


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _matrix(snapshots) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rows: list[list[float]] = []
    labels: list[int] = []
    ids: list[str] = []
    for s in snapshots:
        feats = s.features_json or {}
        rows.append([float(feats.get(c, 0.0) or 0.0) for c in FEATURE_COLUMNS])
        labels.append(1 if feats.get("is_ntl") else 0)
        ids.append(s.entity_id)
    x = np.nan_to_num(np.asarray(rows, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    y = np.asarray(labels, dtype=int)
    return x, y, ids


def _build_classifier(seed: int) -> tuple[Any, str]:
    """Prefer LightGBM; fall back to scikit-learn gradient boosting.

    Both expose ``predict_proba`` and ``feature_importances_`` and are supported by
    SHAP ``TreeExplainer``.
    """
    if _has("lightgbm"):
        try:
            from lightgbm import LGBMClassifier

            return (
                LGBMClassifier(
                    n_estimators=300,
                    learning_rate=0.05,
                    num_leaves=31,
                    random_state=seed,
                    verbose=-1,
                ),
                "lightgbm",
            )
        except Exception:  # pragma: no cover - defensive
            pass
    from sklearn.ensemble import GradientBoostingClassifier

    return (
        GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            random_state=seed,
        ),
        "sklearn-gradient-boosting",
    )


def _proba(classifier: Any, x: np.ndarray) -> np.ndarray:
    if hasattr(classifier, "predict_proba"):
        return np.clip(classifier.predict_proba(x)[:, 1], 0.0, 1.0)
    return np.clip(classifier.predict(x).astype(float), 0.0, 1.0)  # pragma: no cover


def _shap_contributions(classifier: Any, x: np.ndarray) -> np.ndarray | None:
    """Per-row SHAP contributions for the positive class, or None when unavailable."""
    if not _has("shap"):
        return None
    try:
        import shap

        explainer = shap.TreeExplainer(classifier)
        values = explainer.shap_values(x)
        if isinstance(values, list):  # binary classifier -> [class0, class1]
            values = values[-1]
        arr = np.asarray(values, dtype=float)
        if arr.ndim == 3:  # (rows, features, classes)
            arr = arr[..., -1]
        return arr
    except Exception:  # pragma: no cover - shap optional / model unsupported
        return None


def _fallback_contributions(
    x: np.ndarray, importances: np.ndarray
) -> np.ndarray:
    """Deterministic per-row attribution: global importance x standardized value.

    Gives a signed, per-customer contribution even without SHAP, so the UI always
    has feature-level explanations.
    """
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    standardized = (x - mean) / std
    return standardized * importances


def _explanations_for_row(
    contributions: np.ndarray,
    values: np.ndarray,
    top_n: int,
) -> list[dict]:
    order = np.argsort(-np.abs(contributions))[:top_n]
    out: list[dict] = []
    for idx in order:
        col = FEATURE_COLUMNS[idx]
        contribution = float(contributions[idx])
        out.append(
            {
                "feature": f"ml::{col}",
                "label": _FEATURE_LABELS.get(col, col),
                "contribution": round(contribution, 6),
                "direction": "increases" if contribution >= 0 else "decreases",
                "detail": (
                    f"Model attribution for {_FEATURE_LABELS.get(col, col).lower()} "
                    f"(value={round(float(values[idx]), 4)})."
                ),
            }
        )
    return out


def score_customers(snapshots, seed: int = 42, top_n: int = 4) -> MLScoring | None:
    """Train on the current customer population and score every customer.

    Returns ``None`` (caller falls back to the heuristic) when scikit-learn is
    missing or the labelled population is too small/degenerate to train.
    """
    if not snapshots or not ml_available():
        return None

    x, y, ids = _matrix(snapshots)
    positives = int(y.sum())
    negatives = int(len(y) - positives)
    if len(y) < MIN_ROWS or positives < MIN_POSITIVES or negatives < MIN_NEGATIVES:
        return None

    from sklearn.ensemble import IsolationForest

    classifier, algorithm = _build_classifier(seed)
    classifier.fit(x, y)
    proba = _proba(classifier, x)

    anomaly_model = IsolationForest(
        n_estimators=200, random_state=seed, contamination="auto"
    )
    anomaly_model.fit(x)
    inverted = -anomaly_model.score_samples(x)  # higher = more anomalous
    span = float(inverted.max() - inverted.min()) or 1e-9
    anomaly = np.clip((inverted - inverted.min()) / span, 0.0, 1.0)

    if hasattr(classifier, "feature_importances_"):
        importances = np.asarray(classifier.feature_importances_, dtype=float)
    else:  # pragma: no cover
        importances = np.ones(len(FEATURE_COLUMNS), dtype=float)
    imp_total = float(importances.sum()) or 1.0
    importances_norm = importances / imp_total

    contributions = _shap_contributions(classifier, x)
    explain_source = "shap" if contributions is not None else "model-importance"
    if contributions is None:
        contributions = _fallback_contributions(x, importances_norm)

    results: dict[str, CustomerMLResult] = {}
    for i, entity_id in enumerate(ids):
        results[entity_id] = CustomerMLResult(
            supervised_probability=float(proba[i]),
            anomaly_score=float(anomaly[i]),
            explanations=_explanations_for_row(contributions[i], x[i], top_n),
        )

    full_algorithm = f"{algorithm}+isolation-forest+{explain_source}"
    metrics = {
        "n_train": int(len(y)),
        "n_positives": positives,
        "n_negatives": negatives,
        "explain_source": explain_source,
        "seed": seed,
    }
    feature_importances = {
        c: round(float(v), 6)
        for c, v in zip(FEATURE_COLUMNS, importances_norm, strict=False)
    }
    return MLScoring(
        results=results,
        algorithm=full_algorithm,
        metrics=metrics,
        feature_importances=feature_importances,
    )
