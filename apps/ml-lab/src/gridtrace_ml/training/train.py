"""Train a supervised NTL classifier and an IsolationForest anomaly detector.

Prefers gradient-boosted trees (LightGBM, then CatBoost) and falls back to
scikit-learn's ``HistGradientBoostingClassifier`` so the lab runs even when the
heavier libraries are unavailable. All estimators are seeded for determinism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from gridtrace_ml.features import FEATURE_COLUMNS


@dataclass
class ModelBundle:
    classifier: Any
    anomaly: Any
    feature_columns: list[str]
    algorithm: str
    anomaly_score_min: float = 0.0
    anomaly_score_max: float = 1.0
    metadata: dict = field(default_factory=dict)


def _build_classifier(seed: int) -> tuple[Any, str]:
    try:
        from lightgbm import LGBMClassifier

        return (
            LGBMClassifier(
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                random_state=seed,
                verbose=-1,
            ),
            "lightgbm",
        )
    except Exception:  # pragma: no cover - exercised only when lightgbm missing
        pass
    try:
        from catboost import CatBoostClassifier

        return (
            CatBoostClassifier(
                iterations=200,
                learning_rate=0.05,
                depth=6,
                random_seed=seed,
                verbose=False,
            ),
            "catboost",
        )
    except Exception:  # pragma: no cover
        pass
    from sklearn.ensemble import HistGradientBoostingClassifier

    return (
        HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, random_state=seed),
        "sklearn-histgbm",
    )


def train_models(train: pd.DataFrame, seed: int = 42) -> ModelBundle:
    from sklearn.ensemble import IsolationForest

    X = train[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = train["label_is_ntl"].to_numpy(dtype=int)

    classifier, algorithm = _build_classifier(seed)
    classifier.fit(X, y)

    anomaly = IsolationForest(n_estimators=200, random_state=seed, contamination="auto")
    anomaly.fit(X)
    raw = anomaly.score_samples(X)  # higher = more normal
    inverted = -raw  # higher = more anomalous

    bundle = ModelBundle(
        classifier=classifier,
        anomaly=anomaly,
        feature_columns=list(FEATURE_COLUMNS),
        algorithm=algorithm,
        anomaly_score_min=float(inverted.min()),
        anomaly_score_max=float(inverted.max()),
        metadata={"n_train": int(len(train)), "n_positives": int(y.sum()), "seed": seed},
    )
    return bundle
