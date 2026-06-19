"""Dataset construction and leakage-safe splitting for the ML lab."""

from gridtrace_ml.datasets.splits import (
    SplitResult,
    customer_time_split,
    load_dataset,
)

__all__ = ["SplitResult", "customer_time_split", "load_dataset"]
