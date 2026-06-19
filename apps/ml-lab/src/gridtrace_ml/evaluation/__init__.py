"""Evaluation: PR-AUC and precision@K (NOT accuracy) for imbalanced NTL detection."""

from gridtrace_ml.evaluation.metrics import EvaluationReport, evaluate

__all__ = ["EvaluationReport", "evaluate"]
