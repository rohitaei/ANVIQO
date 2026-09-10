import os

os.environ.setdefault("ANVIQO_SECRET_KEY", "phase4-test-secret")
os.environ.setdefault("ANVIQO_ADMIN_USER", "phase4-test-admin")
os.environ.setdefault("ANVIQO_ADMIN_PASSWORD", "phase4-test-password")

import anviqo_phase4_runtime as runtime


def _login(client):
    return client.post("/login", data={"username": "phase4-test-admin", "password": "phase4-test-password"}, follow_redirects=False)


def test_phase4_get_is_authenticated_and_nonfabricating():
    client = runtime.app.test_client()
    _login(client)
    response = client.get("/api/phase4")
    assert response.status_code == 200
    data = response.get_json()
    assert data["phase"] == "PHASE_4"
    assert data["safety"]["plc_write"] is False
    assert data["safety"]["scada_control"] is False
    assert data["domains"]["energy"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_phase4_post_accepts_explicit_evidence():
    client = runtime.app.test_client()
    _login(client)
    response = client.post("/api/phase4", json={"evidence": {
        "energy": {"energy_kwh": 1000, "production_output": 100},
        "production_impact": {"production_output": 100, "production_at_risk": 10},
        "safety": {"permit_status": "ACTIVE"},
        "maintenance": {"candidates": [{"tag": "PT-303", "risk_score": 80}]},
        "reliability": {"prediction_history": [{"tag": "PT-303", "verified": True, "outcome": "FAILURE"}]},
    }})
    assert response.status_code == 200
    data = response.get_json()
    assert data["domains"]["energy"]["status"] == "AVAILABLE"
    assert data["domains"]["production_impact"]["status"] == "AVAILABLE"
    assert data["domains"]["safety"]["status"] == "AVAILABLE"
    assert data["domains"]["maintenance_planner"]["status"] == "AVAILABLE"
    assert data["domains"]["reliability"]["status"] == "AVAILABLE"
