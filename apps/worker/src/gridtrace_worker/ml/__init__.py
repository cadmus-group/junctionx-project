"""Optional ML inference modules (MOMENT TSFM pipeline)."""

from __future__ import annotations

__all__ = ["ml_deps_available", "MOMENTInferencePipeline", "MomentAnomalyResult"]


def ml_deps_available() -> bool:
    """Return True when torch, momentfm, and duckdb are installed.

    Uses importlib metadata only — never imports torch/momentfm in the caller
    process (macOS segfault when combined with LightGBM/SHAP after MOMENT).
    """
    import importlib.util

    return all(
        importlib.util.find_spec(name) is not None
        for name in ("duckdb", "momentfm", "torch")
    )


def __getattr__(name: str):
    if name in ("MOMENTInferencePipeline", "MomentAnomalyResult"):
        from gridtrace_worker.ml.moment_pipeline import MomentAnomalyResult, MOMENTInferencePipeline

        return MOMENTInferencePipeline if name == "MOMENTInferencePipeline" else MomentAnomalyResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
