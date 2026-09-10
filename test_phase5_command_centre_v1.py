import os
from pathlib import Path

os.environ.setdefault("ANVIQO_SECRET_KEY", "phase5-test-secret")
os.environ.setdefault("ANVIQO_ADMIN_USER", "phase5-test-admin")
os.environ.setdefault("ANVIQO_ADMIN_PASSWORD", "phase5-test-password")
_TEST_DB = Path("/tmp/anviqo_phase5_test.db")
_TEST_DB.unlink(missing_ok=True)
os.environ["ANVIQO_TENANT_DB_URL"] = f"sqlite://{_TEST_DB}"

import phase5_command_centre_runtime as runtime


def _login(client):
    return client.post("/login", data={"username": os.environ["ANVIQO_ADMIN_USER"], "password": os.environ["ANVIQO_ADMIN_PASSWORD"]}, follow_redirects=False)


def test_hod_management_get_uses_existing_evidence():
    client = runtime.app.test_client()
    assert _login(client).status_code == 302
    response = client.get("/api/hod-management")
    assert response.status_code == 200
    data = response.get_json()
    assert "evidence_context" in data
    assert data["safety_boundary"]["plc_write"] is False
    assert data["safety_boundary"]["scada_control"] is False


def test_hod_management_post_reuses_supplied_existing_evidence():
    client = runtime.app.test_client()
    _login(client)
    payload = {"executive": {"plant_situation": "ATTENTION", "plant_health": {"status": "DEGRADED", "score": 72}, "top_equipment_risks": [{"equipment": "PT-303", "priority": 84, "status": "URGENT", "reason": "Verified evidence requires review."}]}}
    response = client.post("/api/hod-management", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["top_priorities"][0]["equipment"] == "PT-303"
    assert data["action_queue"]["action_queue"][0]["approval_required"] is True


def test_human_decision_never_executes():
    client = runtime.app.test_client()
    _login(client)
    response = client.post("/api/hod-management/decision", json={"action": {"action_id": "A-1", "equipment": "PT-303", "action": "INSPECT"}, "decision": "APPROVE", "reviewer": "HOD"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["approved"] is True
    assert data["executed"] is False
    assert data["safety_boundary"]["automatic_execution"] is False


def test_management_page_exists():
    client = runtime.app.test_client()
    _login(client)
    response = client.get("/management")
    assert response.status_code == 200
    assert b"HUMAN & MANAGEMENT INTELLIGENCE" in response.data