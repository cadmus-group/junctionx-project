"""GridTrace ML lab.

Experimentation and training environment for non-technical-loss (NTL) detection.
Logic lives in importable modules (datasets, features, training, inference,
evaluation, explainability, registry); notebooks only orchestrate them.

Determinism: the synthetic generator is OWNED by ``gridtrace_worker`` and imported
here so the worker and the lab never diverge. The authoritative risk formulas come
from ``gridtrace_domain``.
"""

__version__ = "0.1.0"

MODEL_VERSION = "ntl-gbm-v1"
FEATURE_VERSION = "features-v1"
