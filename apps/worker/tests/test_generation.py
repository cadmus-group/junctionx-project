"""Deterministic synthetic generation tests (no database)."""

from __future__ import annotations

import numpy as np
from gridtrace_worker.jobs.generate_synthetic import (
    NUM_CUSTOMERS,
    NUM_TIMESTAMPS,
    NUM_TRANSFORMERS,
    SHOWCASE_TRANSFORMER_INDEX,
    build_demo_dataset,
)


def test_generation_is_deterministic():
    a = build_demo_dataset(42)
    b = build_demo_dataset(42)
    assert len(a.customers) == len(b.customers) == NUM_CUSTOMERS
    assert len(a.transformers) == len(b.transformers) == NUM_TRANSFORMERS
    for ca, cb in zip(a.customers, b.customers, strict=True):
        assert ca.external_ref == cb.external_ref
        assert np.allclose(ca.meter_kwh, cb.meter_kwh)
    assert a.showcase == b.showcase


def test_series_shape_and_timestamps():
    ds = build_demo_dataset(42)
    assert len(ds.timestamps) == NUM_TIMESTAMPS
    for c in ds.customers:
        assert c.meter_kwh.shape == (NUM_TIMESTAMPS,)
        assert np.all(c.meter_kwh >= 0.0)


def test_three_incidents_present():
    ds = build_demo_dataset(42)
    incidents = {c.incident for c in ds.customers if c.incident}
    assert incidents == {"partial_bypass", "coordinated_cluster", "meter_fault"}


def test_meter_fault_is_not_labeled_theft():
    ds = build_demo_dataset(42)
    mf = [c for c in ds.customers if c.incident == "meter_fault"]
    assert mf and all(c.is_ntl is False for c in mf)
    theft = [c for c in ds.customers if c.incident in ("partial_bypass", "coordinated_cluster")]
    assert theft and all(c.is_ntl is True for c in theft)


def test_showcase_transformer_reconciliation_and_ratio():
    ds = build_demo_dataset(42)
    s = ds.showcase
    # Energy balance reconciles exactly (within rounding).
    recomputed = s["energy_input_kwh"] - s["metered_kwh"] - s["technical_kwh"]
    assert abs(recomputed - s["unexplained_kwh"]) < 1.0
    assert 0.085 <= s["unexplained_ratio"] <= 0.115
    # Illustrative magnitude target.
    assert 11000 <= s["energy_input_kwh"] <= 13800


def test_showcase_customer_under_reports():
    ds = build_demo_dataset(42)
    showcase = ds.customers[0]
    assert showcase.transformer_idx == SHOWCASE_TRANSFORMER_INDEX
    assert showcase.incident == "partial_bypass"
    # Meter is well below true in the incident window.
    onset = NUM_TIMESTAMPS - 30 * 24
    assert showcase.meter_kwh[onset:].sum() < 0.6 * showcase.true_kwh[onset:].sum()
