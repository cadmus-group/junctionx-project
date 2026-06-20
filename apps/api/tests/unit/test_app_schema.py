from __future__ import annotations

from gridtrace_api.main import create_app

REQUIRED_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/me",
    "/api/v1/dashboard/summary",
    "/api/v1/dashboard/loss-trend",
    "/api/v1/gis/anomalies/geojson",
    "/api/v1/gis/hotspots",
    "/api/v1/assets",
    "/api/v1/assets/{asset_id}",
    "/api/v1/assets/transformers/{transformer_id}/reconciliation",
    "/api/v1/assets/{asset_id}/customers",
    "/api/v1/customers",
    "/api/v1/customers/{customer_id}",
    "/api/v1/customers/{customer_id}/readings",
    "/api/v1/customers/{customer_id}/risk-profile",
    "/api/v1/inspections/queue",
    "/api/v1/inspections/missions",
    "/api/v1/inspections/missions/{mission_id}/cases",
    "/api/v1/inspections/cases/{case_id}",
    "/api/v1/inspections/cases/{case_id}/outcome",
    "/api/v1/inspections/route",
    "/api/v1/models",
    "/api/v1/health",
}


def test_all_required_endpoints_present():
    app = create_app()
    paths = set(app.openapi()["paths"].keys())
    missing = REQUIRED_PATHS - paths
    assert not missing, f"Missing endpoints: {sorted(missing)}"
