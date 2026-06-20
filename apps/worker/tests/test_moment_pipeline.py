"""Unit tests for MOMENT pipeline helpers (no torch required)."""

from __future__ import annotations

import numpy as np
import pytest
from gridtrace_worker.ml.moment_pipeline import (
    MomentAnomalyResult,
    _parse_database_url_for_duckdb,
    build_peak_explanation_entries,
    instance_normalize,
    moment_peak_explanations,
    mse_to_anomaly_scores,
    pad_sequence,
)
from gridtrace_worker.scoring import customer_components, replace_anomaly_component


class TestDatabaseUrlParsing:
    def test_parses_postgres_url(self):
        url = "postgresql://gridtrace:secret@localhost:5432/gridtrace"
        opts = _parse_database_url_for_duckdb(url)
        assert "dbname=gridtrace" in opts
        assert "user=gridtrace" in opts
        assert "password=secret" in opts
        assert "host=localhost" in opts
        assert "port=5432" in opts


class TestPadSequence:
    def test_pads_short_sequence_with_zeros(self):
        values, mask, ts = pad_sequence([1.0, 2.0], ["t1", "t2"], context_length=4)
        assert values.tolist() == [1.0, 2.0, 0.0, 0.0]
        assert mask.tolist() == [1.0, 1.0, 0.0, 0.0]
        assert ts == ["t1", "t2"]

    def test_truncates_long_sequence(self):
        values = list(range(10))
        ts = [f"t{i}" for i in range(10)]
        padded, mask, out_ts = pad_sequence(values, ts, context_length=4)
        assert padded.tolist() == [6.0, 7.0, 8.0, 9.0]
        assert mask.tolist() == [1.0, 1.0, 1.0, 1.0]
        assert out_ts == ["t6", "t7", "t8", "t9"]


class TestInstanceNormalize:
    def test_z_scores_masked_values(self):
        values = np.array([1.0, 3.0, 0.0, 0.0])
        mask = np.array([1.0, 1.0, 0.0, 0.0])
        normed = instance_normalize(values, mask)
        masked = normed[:2]
        assert abs(float(masked.mean())) < 1e-5
        assert np.isfinite(normed).all()

    def test_zero_variance_uses_epsilon(self):
        values = np.array([5.0, 5.0, 0.0, 0.0])
        mask = np.array([1.0, 1.0, 0.0, 0.0])
        normed = instance_normalize(values, mask)
        assert np.isfinite(normed[:2]).all()


class TestMseToAnomalyScores:
    def test_higher_mse_maps_higher(self):
        mse = np.array([0.001, 0.01, 0.1, 0.5, 1.0])
        scores = mse_to_anomaly_scores(mse)
        assert scores[-1] > scores[0]
        assert scores.min() >= 0.0 and scores.max() <= 1.0

    def test_empty_array(self):
        assert mse_to_anomaly_scores(np.array([])).size == 0


class TestPeakExplanations:
    def test_build_peak_entries_shape(self):
        ts = ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z"]
        errors = np.array([0.01, 0.09, 0.02])
        mask = np.ones(3)
        entries = build_peak_explanation_entries(ts, errors, mask, top_k=2)
        assert len(entries) == 2
        assert entries[0]["feature"] == "moment_reconstruction_peak"
        assert "2026-01-01T01:00:00Z" in entries[0]["detail"]

    def test_moment_peak_explanations_from_result(self):
        result = MomentAnomalyResult(
            customer_id="cust-1",
            anomaly_score=0.8,
            reconstruction_mse=0.05,
            peak_timestamps=["2026-01-01T01:00:00Z"],
            peak_errors=[0.09],
        )
        entries = moment_peak_explanations(result)
        assert len(entries) == 1
        assert entries[0]["contribution"] == 1.0


class TestHybridScoring:
    def test_replace_anomaly_recomputes_composite(self):
        feats = {
            "drop_ratio": 0.3,
            "peer_deviation": 0.8,
            "flatline": 0.0,
            "grid_unexplained_ratio": 0.1,
            "spatial_neighborhood_risk": 0.4,
        }
        base = customer_components(feats)
        updated = replace_anomaly_component(base, 0.95)
        assert updated.components.anomaly_score == pytest.approx(0.95)
        assert updated.score >= base.score
        assert updated.tier in ("LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL")


@pytest.mark.ml
def test_moment_pipeline_import_when_ml_deps_present():
    """Optional integration smoke test when ML dependency group is installed."""
    from gridtrace_worker.ml import ml_deps_available

    if not ml_deps_available():
        pytest.skip("ML dependencies not installed (uv sync --group ml)")

    from gridtrace_worker.ml.moment_pipeline import MOMENTInferencePipeline

    assert MOMENTInferencePipeline is not None
