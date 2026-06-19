"""Feature-engineering job: meter/energy readings -> feature_snapshots.

Loads readings up to ``as_of`` (no future data), computes per-customer and
per-transformer features via the pure functions in ``gridtrace_worker.features``,
and writes versioned ``FeatureSnapshot`` rows. Idempotent: existing snapshots for
the same feature version are replaced.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

import numpy as np
from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    FeatureSnapshot,
    MeterReading,
    TechnicalLossEstimate,
)
from gridtrace_domain import unexplained_loss, unexplained_loss_ratio
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from gridtrace_worker.features import (
    FEATURE_VERSION,
    attach_peer_and_spatial,
    customer_feature_vector,
    transformer_feature_vector,
)
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("build_features")


def _timestamp_index(session: Session) -> list[datetime]:
    rows = session.execute(
        select(MeterReading.timestamp).distinct().order_by(MeterReading.timestamp)
    ).all()
    return [r[0] for r in rows]


def _load_customer_series(
    session: Session, ts_index: dict[datetime, int], n: int
) -> dict[str, np.ndarray]:
    series: dict[str, np.ndarray] = {}
    rows = session.execute(
        select(MeterReading.meter_id, MeterReading.timestamp, MeterReading.consumption_kwh)
    ).all()
    for meter_id, ts, kwh in rows:
        arr = series.get(meter_id)
        if arr is None:
            arr = np.zeros(n, dtype=float)
            series[meter_id] = arr
        idx = ts_index.get(ts)
        if idx is not None:
            arr[idx] = float(kwh)
    return series


def _transformer_totals(session: Session) -> dict[str, tuple[float, float]]:
    """asset_id -> (input_total, technical_total) over the full series."""
    input_rows = session.execute(
        select(
            AssetEnergyReading.asset_id,
            func.coalesce(func.sum(AssetEnergyReading.energy_input_kwh), 0.0),
        ).group_by(AssetEnergyReading.asset_id)
    ).all()
    tech_rows = session.execute(
        select(
            TechnicalLossEstimate.asset_id,
            func.coalesce(func.sum(TechnicalLossEstimate.estimated_technical_loss_kwh), 0.0),
        ).group_by(TechnicalLossEstimate.asset_id)
    ).all()
    tech_map = {a: float(t) for a, t in tech_rows}
    return {a: (float(i), tech_map.get(a, 0.0)) for a, i in input_rows}


def run(session: Session, seed: int | None = None) -> dict:
    ts_list = _timestamp_index(session)
    if not ts_list:
        raise RuntimeError("No meter readings found; run generate-synthetic first.")
    n = len(ts_list)
    as_of = ts_list[-1]
    as_of_idx = n - 1
    ts_index = {ts: i for i, ts in enumerate(ts_list)}
    hours = np.array([ts.hour for ts in ts_list])

    customers = session.execute(select(Customer)).scalars().all()
    series = _load_customer_series(session, ts_index, n)
    tx_totals = _transformer_totals(session)

    # Group customers by transformer.
    by_tx: dict[str, list[Customer]] = defaultdict(list)
    for c in customers:
        by_tx[c.transformer_id].append(c)

    # Replace existing snapshots for this feature version (idempotent).
    session.execute(delete(FeatureSnapshot).where(FeatureSnapshot.feature_version == FEATURE_VERSION))

    snapshot_rows: list[dict] = []
    transformer_ratio: dict[str, float] = {}
    transformer_unexplained: dict[str, float] = {}
    transformer_metered: dict[str, float] = {}

    # Per-transformer ratios from the authoritative domain formula.
    for tx_id, members in by_tx.items():
        metered_total = float(sum(series.get(c.id, np.zeros(n)).sum() for c in members))
        input_total, technical_total = tx_totals.get(tx_id, (0.0, 0.0))
        unexp = unexplained_loss(input_total, metered_total, technical_total)
        ratio = unexplained_loss_ratio(unexp, input_total)
        transformer_ratio[tx_id] = ratio
        transformer_unexplained[tx_id] = unexp
        transformer_metered[tx_id] = metered_total

    # Customer features.
    for tx_id, members in by_tx.items():
        ratio = transformer_ratio.get(tx_id, 0.0)
        cust_features: dict[str, dict] = {}
        cust_nb: dict[str, str] = {}
        ref_to_id: dict[str, str] = {}
        for c in members:
            arr = series.get(c.id, np.zeros(n))
            feats = customer_feature_vector(arr, hours, as_of_idx)
            cust_features[c.external_ref] = feats
            cust_nb[c.external_ref] = c.region_id or ""
            ref_to_id[c.external_ref] = c.id
        attach_peer_and_spatial(cust_features, cust_nb, ratio)

        for c in members:
            feats = cust_features[c.external_ref]
            feats["parent_transformer_entity_id"] = tx_id
            feats["incident"] = (c.metadata_json or {}).get("incident")
            feats["is_ntl"] = bool((c.metadata_json or {}).get("is_ntl", False))
            snapshot_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "entity_type": "customer",
                    "entity_id": c.id,
                    "as_of": as_of,
                    "features_json": feats,
                    "feature_version": FEATURE_VERSION,
                }
            )

        # Transformer features.
        input_total, technical_total = tx_totals.get(tx_id, (0.0, 0.0))
        tx_feats = transformer_feature_vector(
            cust_features,
            transformer_ratio.get(tx_id, 0.0),
            input_total,
            transformer_metered.get(tx_id, 0.0),
            technical_total,
            transformer_unexplained.get(tx_id, 0.0),
        )
        snapshot_rows.append(
            {
                "id": str(uuid.uuid4()),
                "entity_type": "transformer",
                "entity_id": tx_id,
                "as_of": as_of,
                "features_json": tx_feats,
                "feature_version": FEATURE_VERSION,
            }
        )

    for i in range(0, len(snapshot_rows), 2000):
        session.execute(insert(FeatureSnapshot), snapshot_rows[i : i + 2000])

    log_event(
        logger,
        "features_built",
        feature_version=FEATURE_VERSION,
        as_of=as_of,
        customer_count=len(customers),
        transformer_count=len(by_tx),
        snapshots=len(snapshot_rows),
    )
    return {
        "as_of": as_of,
        "feature_version": FEATURE_VERSION,
        "snapshots": len(snapshot_rows),
        "transformer_count": len(by_tx),
    }
