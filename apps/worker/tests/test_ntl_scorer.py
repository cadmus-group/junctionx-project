"""Tests for the live supervised + IsolationForest NTL scorer."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pytest
from gridtrace_worker.ml import ntl_scorer


@dataclass
class FakeSnapshot:
    entity_id: str
    entity_type: str
    features_json: dict


def _make_population(n: int = 200, seed: int = 7) -> list[FakeSnapshot]:
    rng = random.Random(seed)
    snaps: list[FakeSnapshot] = []
    for i in range(n):
        is_ntl = i % 5 == 0  # 20% positives
        if is_ntl:
            drop_ratio = rng.uniform(0.3, 0.7)
            peer_deviation = rng.uniform(0.3, 0.8)
            anomaly_z = rng.uniform(2.0, 5.0)
            grid_ratio = rng.uniform(0.08, 0.2)
        else:
            drop_ratio = rng.uniform(0.9, 1.1)
            peer_deviation = rng.uniform(-0.1, 0.1)
            anomaly_z = rng.uniform(0.0, 1.0)
            grid_ratio = rng.uniform(0.0, 0.03)
        snaps.append(
            FakeSnapshot(
                entity_id=f"cust-{i}",
                entity_type="customer",
                features_json={
                    "baseline_mean_kwh": rng.uniform(1.0, 3.0),
                    "recent_mean_kwh": rng.uniform(0.5, 3.0),
                    "drop_ratio": drop_ratio,
                    "trend": drop_ratio - 1.0,
                    "night_day_ratio": rng.uniform(0.2, 0.6),
                    "zero_fraction": rng.uniform(0.0, 0.3),
                    "flatline": 0.0,
                    "anomaly_z": anomaly_z,
                    "peer_deviation": peer_deviation,
                    "grid_unexplained_ratio": grid_ratio,
                    "spatial_neighborhood_risk": rng.uniform(0.0, 0.4),
                    "is_ntl": is_ntl,
                },
            )
        )
    return snaps


def test_ml_available() -> None:
    assert ntl_scorer.ml_available() is True


def test_returns_none_for_small_population() -> None:
    snaps = _make_population(n=10)
    assert ntl_scorer.score_customers(snaps) is None


def test_returns_none_without_positives() -> None:
    snaps = _make_population(n=100)
    for s in snaps:
        s.features_json["is_ntl"] = False
    assert ntl_scorer.score_customers(snaps) is None


def test_scores_every_customer_with_valid_ranges() -> None:
    snaps = _make_population()
    scoring = ntl_scorer.score_customers(snaps)
    assert scoring is not None
    assert len(scoring.results) == len(snaps)
    assert "isolation-forest" in scoring.algorithm
    for res in scoring.results.values():
        assert 0.0 <= res.supervised_probability <= 1.0
        assert 0.0 <= res.anomaly_score <= 1.0
        assert res.explanations  # non-empty feature-level explanations
        for item in res.explanations:
            assert item["feature"].startswith("ml::")
            assert item["direction"] in {"increases", "decreases"}


def test_separates_theft_from_normal() -> None:
    snaps = _make_population()
    scoring = ntl_scorer.score_customers(snaps)
    assert scoring is not None
    pos = [
        scoring.results[s.entity_id].supervised_probability
        for s in snaps
        if s.features_json["is_ntl"]
    ]
    neg = [
        scoring.results[s.entity_id].supervised_probability
        for s in snaps
        if not s.features_json["is_ntl"]
    ]
    # The trained classifier should rank theft cases higher on average.
    assert sum(pos) / len(pos) > sum(neg) / len(neg)


def test_deterministic_with_seed() -> None:
    snaps = _make_population()
    a = ntl_scorer.score_customers(snaps, seed=123)
    b = ntl_scorer.score_customers(snaps, seed=123)
    assert a is not None and b is not None
    for entity_id, res in a.results.items():
        assert res.supervised_probability == pytest.approx(
            b.results[entity_id].supervised_probability
        )
        assert res.anomaly_score == pytest.approx(b.results[entity_id].anomaly_score)
