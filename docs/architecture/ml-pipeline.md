# ML pipeline

The ML lifecycle lives in `apps/ml-lab` (`gridtrace_ml`); batch scoring for the app
runs in `apps/worker`. **Heavy work never runs inside API request handlers.**

## Stages

1. **datasets / synthetic** — deterministic generation seeded by `DEMO_SEED`.
2. **features** — importable feature functions (no notebook-only logic). Split by
   customer **and** time; only use data up to `as_of` to prevent future leakage.
3. **training** — CatBoost / LightGBM (supervised) + Isolation Forest (anomaly),
   built on scikit-learn.
4. **evaluation** — report **precision-recall AUC** and **precision@K**. Accuracy is
   *not* the primary metric (severe class imbalance).
5. **explainability** — SHAP contributions feed the customer evidence panel.
6. **registry** — model + metrics + metadata sidecar saved beside artifacts; analytical
   data stored as Parquet. A `model_registry` row marks the active version.

## Scoring outputs

Each scored entity gets the five `[0,1]` component scores, the composite 0–100 score,
tier, confidence, estimated loss (kWh + value), inspection priority, explanations,
and `model_version` + `feature_version`. Publication is **atomic** (`is_current`).
