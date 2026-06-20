"""Optional ML inference modules (MOMENT TSFM pipeline)."""

from __future__ import annotations

__all__ = ["ml_deps_available", "MOMENTInferencePipeline", "MomentAnomalyResult"]


def ml_deps_available() -> bool:
    """Return True when torch, momentfm, and duckdb are importable."""
    try:
        import duckdb  # noqa: F401
        import momentfm  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def __getattr__(name: str):
    if name in ("MOMENTInferencePipeline", "MomentAnomalyResult"):
        from gridtrace_worker.ml.moment_pipeline import MomentAnomalyResult, MOMENTInferencePipeline

        return MOMENTInferencePipeline if name == "MOMENTInferencePipeline" else MomentAnomalyResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
