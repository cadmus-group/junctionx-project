# API reference

The authoritative reference is the live OpenAPI document at
`http://localhost:8000/docs` (and `packages/contracts/openapi.json`). All responses
are JSON; errors are RFC 7807 problem details (`application/problem+json`).

Base prefix: `/api/v1`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/login` | Demo login → JWT |
| GET | `/dashboard/summary` | System-wide KPIs |
| GET | `/dashboard/loss-trend` | Daily energy balance trend |
| GET | `/gis/anomalies/geojson` | Customer risk points (FeatureCollection, bbox + min_risk) |
| GET | `/gis/hotspots` | Aggregated risk hotspot cells (FeatureCollection) |
| GET | `/assets` | List/search grid assets |
| GET | `/assets/{id}` | Asset detail |
| GET | `/assets/transformers/{id}/reconciliation` | Energy reconciliation (waterfall) |
| GET | `/assets/{id}/customers` | Downstream customers ranked by risk |
| GET | `/customers` | Risk-ranked customers (filters: min_risk, tier, q) |
| GET | `/customers/{id}` | Customer detail |
| GET | `/customers/{id}/readings` | Meter readings (from/to) |
| GET | `/customers/{id}/risk-profile` | Score, components, peers, explanations, attribution |
| GET | `/inspections/queue` | Prioritized inspection queue |
| POST | `/inspections/missions` | Create mission |
| POST | `/inspections/missions/{id}/cases` | Add case to mission |
| PATCH | `/inspections/cases/{id}` | Update case |
| POST | `/inspections/cases/{id}/outcome` | Record outcome |
| POST | `/inspections/route` | Build a route over customers |
| GET | `/models` | Model registry |
| GET | `/health` | Liveness + DB + demo mode |

Risk responses always include `model_version` and `feature_version`, explicit units,
and currency where monetary values appear.
