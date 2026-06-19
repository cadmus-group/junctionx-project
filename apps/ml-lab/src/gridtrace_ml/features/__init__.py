"""Importable feature engineering for the ML lab.

Promotes notebook logic into modules. Reuses the worker's pure feature functions so
features are identical to what is computed in production scoring.
"""

from gridtrace_ml.features.matrix import (
    FEATURE_COLUMNS,
    build_feature_frame,
    customer_feature_records,
)

__all__ = ["FEATURE_COLUMNS", "build_feature_frame", "customer_feature_records"]
