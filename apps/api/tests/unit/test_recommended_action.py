from __future__ import annotations

from types import SimpleNamespace

from gridtrace_api.modules.inspections.service import recommended_action


def _risk(**kwargs):
    base = {
        "anomaly_score": 0.0,
        "supervised_probability": 0.0,
        "risk_tier": "LOW",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_meter_fault_recommends_diagnostics():
    risk = _risk(anomaly_score=0.9, supervised_probability=0.2, risk_tier="HIGH")
    assert "meter diagnostics" in recommended_action(risk).lower()


def test_high_risk_recommends_field_inspection():
    risk = _risk(anomaly_score=0.5, supervised_probability=0.8, risk_tier="CRITICAL")
    assert "field inspection" in recommended_action(risk).lower()


def test_low_risk_monitors():
    risk = _risk(anomaly_score=0.1, supervised_probability=0.1, risk_tier="LOW")
    assert "monitor" in recommended_action(risk).lower()
