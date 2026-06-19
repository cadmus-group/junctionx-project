"""SHAP-based explanations with a deterministic feature-importance fallback."""

from gridtrace_ml.explainability.shap_explain import (
    explain_customer,
    global_importances,
)

__all__ = ["explain_customer", "global_importances"]
