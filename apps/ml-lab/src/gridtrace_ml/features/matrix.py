"""Build a tabular feature matrix from the synthetic dataset.

Reuses ``gridtrace_worker.features`` so the columns match production scoring. The
matrix has one row per customer at a given ``as_of_idx`` (no future data is read).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from gridtrace_worker.features import (
    attach_peer_and_spatial,
    customer_feature_vector,
)
from gridtrace_worker.jobs.generate_synthetic import DemoDataset

# Numeric feature columns fed to the model (order is stable for reproducibility).
FEATURE_COLUMNS = [
    "baseline_mean_kwh",
    "recent_mean_kwh",
    "drop_ratio",
    "trend",
    "night_day_ratio",
    "zero_fraction",
    "flatline",
    "anomaly_z",
    "peer_deviation",
    "grid_unexplained_ratio",
    "spatial_neighborhood_risk",
]


def _transformer_ratio(ds: DemoDataset, tx_index: int) -> float:
    if tx_index == 0:
        return ds.showcase["unexplained_ratio"]
    tx = ds.transformers[tx_index]
    members = [c for c in ds.customers if c.transformer_idx == tx_index]
    metered = float(sum(c.meter_kwh.sum() for c in members))
    input_total = float(tx.input_kwh.sum())
    technical = float(tx.technical_kwh.sum())
    unexp = input_total - metered - technical
    return unexp / max(input_total, 1e-9)


def customer_feature_records(ds: DemoDataset, as_of_idx: int) -> list[dict]:
    """Per-customer feature dicts with labels and grouping keys."""
    hours = np.array([ts.hour for ts in ds.timestamps])
    records: list[dict] = []
    by_tx: dict[int, list] = {}
    for c in ds.customers:
        by_tx.setdefault(c.transformer_idx, []).append(c)

    for tx_index, members in by_tx.items():
        ratio = _transformer_ratio(ds, tx_index)
        feats: dict[str, dict] = {}
        nb: dict[str, str] = {}
        for c in members:
            feats[c.external_ref] = customer_feature_vector(c.meter_kwh, hours, as_of_idx)
            nb[c.external_ref] = str(c.neighborhood_idx)
        attach_peer_and_spatial(feats, nb, ratio)
        for c in members:
            row = {
                "external_ref": c.external_ref,
                "transformer_idx": c.transformer_idx,
                "neighborhood_idx": c.neighborhood_idx,
                "incident": c.incident,
                "label_is_ntl": int(bool(c.is_ntl)),
                **{k: feats[c.external_ref].get(k, 0.0) for k in FEATURE_COLUMNS},
            }
            records.append(row)
    return records


def build_feature_frame(ds: DemoDataset, as_of_idx: int | None = None) -> pd.DataFrame:
    if as_of_idx is None:
        as_of_idx = len(ds.timestamps) - 1
    return pd.DataFrame(customer_feature_records(ds, as_of_idx))
