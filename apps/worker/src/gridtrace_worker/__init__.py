"""GridTrace background worker.

Owns deterministic synthetic data generation, feature engineering, and risk
scoring. All authoritative formulas are imported from ``gridtrace_domain`` and all
persistence uses the ORM models defined in ``gridtrace_api.db.models`` so the
worker never duplicates domain logic or schema.
"""

__version__ = "0.1.0"

FEATURE_VERSION = "features-v1"
MODEL_VERSION = "ntl-moment-hybrid-v1"
