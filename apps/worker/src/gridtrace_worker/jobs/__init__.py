"""Worker batch jobs.

Each job is idempotent, deterministic given ``DEMO_SEED``, and emits structured
logs. Heavy work (generation, feature engineering, scoring) lives here and never
in API request handlers.
"""
