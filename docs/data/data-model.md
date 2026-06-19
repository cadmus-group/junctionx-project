# Data model

PostgreSQL 15+ with PostGIS (SRID 4326) and pgcrypto. Core tables:

| Table | Purpose |
|-------|---------|
| `operators` | distribution operator (name, country, timezone, currency) |
| `regions` | hierarchical admin/grid regions with geometry |
| `grid_assets` | substations, feeders, transformers, lines, meters (geometry, capacity) |
| `customers` | metered connections (transformer/feeder/region links, point geometry) |
| `meter_readings` | per-meter time series (consumption, voltage, current, PF, quality) |
| `asset_energy_readings` | per-asset energy in/out time series |
| `technical_loss_estimates` | estimated technical losses per asset |
| `feature_snapshots` | computed features per entity + `feature_version` |
| `risk_scores` | composite + component scores, loss/value, priority, explanations, versions |
| `alerts` | surfaced anomalies linked to risk scores |
| `inspection_missions` | planned field missions with route geometry |
| `inspection_cases` | per-customer cases within a mission |
| `inspection_outcomes` | recorded field results and recovery estimates |
| `model_registry` | trained model versions + metrics |
| `audit_logs` | actions for traceability |

## Key indexes

- GIST on `regions.geometry`, `grid_assets.geometry`, `customers.geometry`
- `(meter_id, timestamp)` on `meter_readings`
- `transformer_id` on `customers`
- `(entity_type, entity_id, scored_at)` on `risk_scores`
- `(risk_score, inspection_priority)` ranking index on `risk_scores`

## Conventions

- Timestamps are timezone-aware UTC.
- JSON columns (`*_json`) use JSONB.
- Risk score history is preserved; the active row is flagged `is_current`.
