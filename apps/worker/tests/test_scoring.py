"""Feature + scoring tests (pure, no database)."""

from __future__ import annotations

import numpy as np
from gridtrace_worker.features import (
    attach_peer_and_spatial,
    customer_feature_vector,
    transformer_feature_vector,
    window_slices,
)
from gridtrace_worker.jobs.generate_synthetic import (
    METER_FAULT_TRANSFORMER_INDEX,
    SHOWCASE_TRANSFORMER_INDEX,
    build_demo_dataset,
)
from gridtrace_worker.scoring import customer_components, transformer_components


def _features_for_transformer(ds, tx_index):
    hours = np.array([ts.hour for ts in ds.timestamps])
    as_of_idx = len(ds.timestamps) - 1
    members = [c for c in ds.customers if c.transformer_idx == tx_index]
    feats: dict[str, dict] = {}
    nb: dict[str, str] = {}
    for c in members:
        feats[c.external_ref] = customer_feature_vector(c.meter_kwh, hours, as_of_idx)
        nb[c.external_ref] = str(c.neighborhood_idx)
    ratio = ds.showcase["unexplained_ratio"] if tx_index == SHOWCASE_TRANSFORMER_INDEX else 0.02
    attach_peer_and_spatial(feats, nb, ratio)
    return members, feats


def test_window_slices_have_no_overlap():
    base, recent = window_slices(1000)
    base_idx = set(range(*base.indices(1001)))
    recent_idx = set(range(*recent.indices(1001)))
    assert base_idx.isdisjoint(recent_idx)
    # Recent never reaches beyond as_of (no future leakage).
    assert max(recent_idx) == 1000


def test_component_scores_in_unit_interval():
    ds = build_demo_dataset(42)
    _, feats = _features_for_transformer(ds, SHOWCASE_TRANSFORMER_INDEX)
    for f in feats.values():
        scored = customer_components(f)
        c = scored.components
        for v in (
            c.supervised_probability,
            c.anomaly_score,
            c.grid_imbalance_score,
            c.peer_score,
            c.spatial_score,
        ):
            assert 0.0 <= v <= 1.0
        assert 0.0 <= scored.score <= 100.0


def test_showcase_customer_is_critical():
    ds = build_demo_dataset(42)
    members, feats = _features_for_transformer(ds, SHOWCASE_TRANSFORMER_INDEX)
    showcase_ref = ds.showcase["customer_external_ref"]
    scored = customer_components(feats[showcase_ref])
    assert scored.score >= 85.0, f"showcase score {scored.score}"
    assert scored.tier == "CRITICAL"


def test_meter_fault_low_supervised_high_anomaly():
    ds = build_demo_dataset(42)
    mf = next(c for c in ds.customers if c.incident == "meter_fault")
    members, feats = _features_for_transformer(ds, METER_FAULT_TRANSFORMER_INDEX)
    f = feats[mf.external_ref]
    scored = customer_components(f)
    # Drives the API's "run meter diagnostics" recommendation.
    assert scored.components.anomaly_score >= 0.7
    assert scored.components.supervised_probability < 0.4


def test_transformer_score_in_range_and_showcase_high():
    ds = build_demo_dataset(42)
    members, feats = _features_for_transformer(ds, SHOWCASE_TRANSFORMER_INDEX)
    tx_feats = transformer_feature_vector(
        feats,
        ds.showcase["unexplained_ratio"],
        ds.showcase["energy_input_kwh"],
        ds.showcase["metered_kwh"],
        ds.showcase["technical_kwh"],
        ds.showcase["unexplained_kwh"],
    )
    scored = transformer_components(tx_feats)
    assert 0.0 <= scored.score <= 100.0
    assert scored.tier in ("HIGH", "CRITICAL")


def test_no_customer_overlap_between_transformers():
    ds = build_demo_dataset(42)
    seen: set[str] = set()
    for c in ds.customers:
        assert c.external_ref not in seen
        seen.add(c.external_ref)
