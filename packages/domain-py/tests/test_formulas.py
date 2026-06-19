import math

import pytest
from gridtrace_domain import (
    RiskComponents,
    customer_loss_attribution,
    estimated_loss_value,
    inspection_priority,
    normalize_priority,
    risk_score,
    risk_tier_for_score,
    unexplained_loss,
    unexplained_loss_ratio,
)


class TestUnexplainedLoss:
    def test_positive_unexplained_loss(self):
        # Showcase values from the spec.
        result = unexplained_loss(12400, [10550], 620)
        assert result == pytest.approx(1230)

    def test_zero_unexplained_loss(self):
        assert unexplained_loss(1000, [900], 100) == pytest.approx(0)

    def test_negative_residual_preserved(self):
        assert unexplained_loss(1000, [1100], 50) == pytest.approx(-150)

    def test_partial_downstream_data(self):
        assert unexplained_loss(1000, [300, 200], 100) == pytest.approx(400)

    def test_scalar_consumption(self):
        assert unexplained_loss(1000, 800, 100) == pytest.approx(100)


class TestLossRatio:
    def test_ratio(self):
        assert unexplained_loss_ratio(1230, 12400) == pytest.approx(0.0992, abs=1e-4)

    def test_zero_energy_in_uses_epsilon(self):
        assert math.isfinite(unexplained_loss_ratio(5, 0))


class TestRiskScore:
    def test_all_ones(self):
        c = RiskComponents(1, 1, 1, 1, 1)
        assert risk_score(c) == pytest.approx(100.0)

    def test_all_zeros(self):
        c = RiskComponents(0, 0, 0, 0, 0)
        assert risk_score(c) == pytest.approx(0.0)

    def test_weighted(self):
        c = RiskComponents(0.5, 0.5, 0.5, 0.5, 0.5)
        assert risk_score(c) == pytest.approx(50.0)

    def test_in_range(self):
        c = RiskComponents(0.9, 0.8, 0.7, 0.6, 0.5)
        score = risk_score(c)
        assert 0 <= score <= 100

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            risk_score(RiskComponents(1.5, 0, 0, 0, 0))


class TestRiskTiers:
    @pytest.mark.parametrize(
        ("score", "tier"),
        [
            (0, "LOW"),
            (29, "LOW"),
            (30, "WATCH"),
            (49, "WATCH"),
            (50, "MEDIUM"),
            (69, "MEDIUM"),
            (70, "HIGH"),
            (84, "HIGH"),
            (85, "CRITICAL"),
            (100, "CRITICAL"),
        ],
    )
    def test_thresholds(self, score, tier):
        assert risk_tier_for_score(score) == tier


class TestAttribution:
    def test_share(self):
        result = customer_loss_attribution(3, [3, 1, 1], 1000)
        assert result == pytest.approx(600)

    def test_zero_total_weight(self):
        assert customer_loss_attribution(0, [0, 0], 1000) == 0.0


class TestFinancialValue:
    def test_value(self):
        assert estimated_loss_value(1230, 0.25) == pytest.approx(307.5)


class TestInspectionPriority:
    def test_priority(self):
        # 0.8 * 1000 * 0.9 - 100 = 620
        assert inspection_priority(0.8, 1000, 0.9, 100) == pytest.approx(620)

    def test_normalize(self):
        assert normalize_priority(620, [100, 620, 360]) == pytest.approx(100.0)
        assert normalize_priority(100, [100, 620, 360]) == pytest.approx(0.0)
