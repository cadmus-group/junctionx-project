# Production CSV ingest

Place your operational data under **`data/raw/production/`** (or set `DATA_RAW_PATH` in `.env`).

## Quick start (full demo dataset via CSV path)

```bash
pnpm db:migrate
pnpm db:ingest-production   # exports demo CSVs if needed, then ingests + scores
```

Login after ingest: `demo_operator` / `SuperSecret123!`

To export CSVs without ingesting:

```bash
pnpm db:export-production
```

## Required files

### `operators.csv`
| Column | Required | Example |
|--------|----------|---------|
| name | yes | Demo Operator |
| country_code | yes | NLD |
| timezone | no | Europe/Amsterdam |
| default_currency | no | EUR |

### `grid_assets.csv`
| Column | Required | Example |
|--------|----------|---------|
| external_id | yes | TX-001 |
| asset_type | yes | transformer |
| name | yes | Transformer 001 |
| operator_name | yes | Demo Operator |
| lon | yes | 4.9041 |
| lat | yes | 52.3676 |
| parent_external_id | no | FD-001 |
| voltage_level | no | lv |
| capacity_kva | no | 630 |

### `customers.csv`
| Column | Required | Example |
|--------|----------|---------|
| external_ref | yes | CUST-00001 |
| customer_type | yes | residential |
| operator_name | yes | Demo Operator |
| lon | yes | 4.9042 |
| lat | yes | 52.3677 |
| transformer_external_id | no | TX-001 |
| feeder_external_id | no | FD-001 |
| region_code | no | AMS-N1 |
| zipcode | no | 1012AB |
| building_type | no | apartment |
| tariff_type | no | single |
| incident | no | partial_bypass |
| is_ntl | no | true |

Optional `incident` / `is_ntl` columns populate `customers.metadata_json` for evaluation labels during scoring.

### `meter_readings.csv`
| Column | Required | Example |
|--------|----------|---------|
| customer_external_ref | yes | CUST-00001 |
| timestamp | yes | 2026-01-01T00:00:00Z |
| consumption_kwh | yes | 1.25 |
| voltage | no | 230 |
| power_factor | no | 0.95 |
| reading_quality | no | good |
| source | no | ami |

## Optional files

### `regions.csv`
| Column | Required |
|--------|----------|
| code | yes |
| name | yes |
| region_type | yes |
| operator_name | yes |
| parent_code | no |

### `asset_energy_readings.csv`
Required for meaningful transformer energy reconciliation and risk scoring.

| Column | Required |
|--------|----------|
| asset_external_id | yes |
| timestamp | yes |
| energy_input_kwh | yes |
| energy_output_kwh | no |
| reading_quality | no |
| source | no |

### `technical_loss_estimates.csv`
Pairs with asset energy readings for unexplained-loss calculation.

| Column | Required |
|--------|----------|
| asset_external_id | yes |
| timestamp | yes |
| estimated_technical_loss_kwh | yes |
| method | no |
| confidence | no |

## Commands

```bash
# Export deterministic demo dataset as CSV files (same physics as pnpm db:seed)
pnpm db:export-production
python -m gridtrace_worker.main export-production-csv --seed 42

# Master data only
python -m gridtrace_worker.main ingest-operators
python -m gridtrace_worker.main ingest-grid
python -m gridtrace_worker.main ingest-customers

# Meter readings (requires master data)
python -m gridtrace_worker.main ingest-readings

# Full pipeline: CSV -> enrich -> features -> score
pnpm db:ingest-production
# Merge instead of replacing demo data:
python -m gridtrace_worker.main ingest-production --keep-existing

# Restore login user after manual DB changes
pnpm db:ensure-demo-user
```

## Idempotency

Re-running ingest **updates** existing rows matched by:
- operators: `name`
- grid assets: `(operator_id, external_id)`
- customers: `(operator_id, external_ref)`
- readings: `(meter_id, timestamp)`
- asset energy / technical loss: `(asset_id, timestamp)`

Requires migration `0005_production_ingest_indexes`.

## vs demo seed

| | `pnpm db:seed` | `pnpm db:ingest-production` |
|--|----------------|------------------------------|
| Data source | Synthetic generator (direct to DB) | Your CSV files |
| Use case | Hackathon / offline demo | Real operations / CSV-based workflow |
| Showcase invariants | Yes (built-in) | Yes when using `db:export-production` output |

Schema templates live in `data/raw/production/*.csv.example`.
