"""Evaluation metrics for an imbalanced detection problem.

The PRIMARY metrics are precision-recall AUC (average precision) and precision@K,
because NTL is rare and accuracy is misleading. Accuracy is reported only as a
secondary, contextual number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class EvaluationReport:
    pr_auc: float
    precision_at_k: float
    k: int
    positives: int
    n: int
    recall_at_k: float
    accuracy: float
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pr_auc": round(self.pr_auc, 4),
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "k": self.k,
            "positives": self.positives,
            "n": self.n,
            "accuracy": round(self.accuracy, 4),
            "primary_metric": "pr_auc",
            **self.extra,
        }


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    if labels.sum() == 0:
        return 0.0
    order = np.argsort(-scores, kind="stable")
    y = labels[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / labels.sum()
    ap = 0.0
    prev = 0.0
    for p, r in zip(precision, recall, strict=False):
        ap += p * (r - prev)
        prev = r
    return float(ap)


def evaluate(labels: np.ndarray, scores: np.ndarray, k: int = 20) -> EvaluationReport:
    labels = np.asarray(labels).astype(int)
    scores = np.asarray(scores).astype(float)
    n = labels.size
    positives = int(labels.sum())
    k_eff = min(k, n)
    order = np.argsort(-scores, kind="stable")
    top = order[:k_eff]
    precision_at_k = float(labels[top].mean()) if k_eff else 0.0
    recall_at_k = float(labels[top].sum() / positives) if positives else 0.0

    # Secondary, contextual accuracy at a 0.5 cutoff on a 0-100 score (=> 50).
    preds = (scores >= 50.0).astype(int) if scores.max() > 1.0 else (scores >= 0.5).astype(int)
    accuracy = float((preds == labels).mean()) if n else 0.0

    return EvaluationReport(
        pr_auc=_average_precision(labels, scores),
        precision_at_k=precision_at_k,
        k=k_eff,
        positives=positives,
        n=n,
        recall_at_k=recall_at_k,
        accuracy=accuracy,
    )
