"""Smoke-test the live API against the real database via TestClient.

Validates auth (DB-backed JWT login) and that the dashboard / customers / GIS
endpoints serve the ML-derived risk scores. Run:

    uv run --python 3.11 --package gridtrace-api python scripts/smoke_api.py
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from gridtrace_api.main import create_app

USERNAME = "demo_operator"
PASSWORD = "SuperSecret123!"


def main() -> int:
    app = create_app()
    with TestClient(app) as client:
        # --- Auth: wrong password must fail ---
        bad = client.post(
            "/api/v1/auth/login", json={"username": USERNAME, "password": "wrong-password-xx"}
        )
        assert bad.status_code == 401, f"expected 401 for bad password, got {bad.status_code}"

        # --- Auth: correct credentials ---
        login = client.post(
            "/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
        )
        assert login.status_code == 200, f"login failed: {login.status_code} {login.text}"
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[auth] login OK, role={login.json().get('user', {}).get('role')}")

        # --- Protected route without token must 401 ---
        unauth = client.get("/api/v1/dashboard/summary")
        assert unauth.status_code == 401, f"expected 401 without token, got {unauth.status_code}"

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        print(f"[auth] /me OK: {me.json()}")

        # --- Dashboard summary (reads risk_scores is_current) ---
        summary = client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200, summary.text
        s = summary.json()
        print(
            f"[dashboard] customers={s['total_customers']} "
            f"transformers={s['total_transformers']} "
            f"high={s['high_risk_count']} critical={s['critical_risk_count']} "
            f"loss_kwh={s['total_unexplained_loss_kwh']} model={s['model_version']}"
        )
        assert s["total_customers"] > 0

        # --- Customers list (ML-scored, top risk) ---
        customers = client.get(
            "/api/v1/customers", params={"min_risk": 70, "page": 1, "page_size": 5}, headers=headers
        )
        assert customers.status_code == 200, customers.text
        items = customers.json()["items"]
        print(f"[customers] high-risk returned={len(items)}")
        if items:
            top = items[0]
            print(
                f"[customers] top risk_score={top.get('risk_score')} tier={top.get('risk_tier')}"
            )

            # --- Risk profile carries ML explanations ---
            prof = client.get(
                f"/api/v1/customers/{top['id']}/risk-profile", headers=headers
            )
            assert prof.status_code == 200, prof.text
            explanations = prof.json().get("risk", {}).get("explanations", [])
            ml_expl = [e for e in explanations if str(e.get("feature", "")).startswith("ml::")]
            print(f"[customers] explanations={len(explanations)} ml_explanations={len(ml_expl)}")
            assert ml_expl, "expected ML (ml::) explanations in risk profile"

        # --- GIS anomalies GeoJSON ---
        gis = client.get(
            "/api/v1/gis/anomalies/geojson", params={"min_risk": 50}, headers=headers
        )
        assert gis.status_code == 200, gis.text
        feats = gis.json().get("features", [])
        print(f"[gis] anomaly features={len(feats)}")

        # --- Model registry exposes the active ML algorithm ---
        models = client.get("/api/v1/models", headers=headers)
        assert models.status_code == 200, models.text
        active = [m for m in models.json() if m.get("is_active")]
        if active:
            print(f"[models] active algorithm={active[0].get('algorithm')}")

    print("\nALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
