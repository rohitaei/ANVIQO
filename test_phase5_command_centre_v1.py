import os

os.environ.setdefault("ANVIQO_SECRET_KEY", "phase5-test-secret")
os.environ.setdefault("ANVIQO_ADMIN_USER", "phase5-test-admin")
os.environ.setdefault("ANVIQO_ADMIN_PASSWORD", "phase5-test-password")
os.environ.setdefault("ANVIQO_TENANT_DB_URL", "sqlite:////tmp/anviqo_phase5_test.db")

from phase5_command_centre_runtime import app


def test_management_get_is_safe_and_evidence_empty():
    client = app.test_client()
    with client.session_transaction() as session:
        session["authenticated"] = True
        session["username"] = "phase5-test-admin"
        session["user_id"] = "u1"
        session["organization_id"] = "org1"
        session["plant_id"] = "plant1"
        session["role"] = "ADMIN"
    response = client.get("/api/management")
    assert response.status_code == 200
    data = response.get_json()
    assert data["management_state"] == "INSUFFICIENT_EVIDENCE"
    assert data["safety_boundary"]["plc_write"] is False
    assert data["safety_boundary"]["scada_control"] is False


def test_management_post_reuses_supplied_existing_evidence():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({"authenticated": True, "username": "phase5-test-admin", "user_id": "u1", "organization_id": "org1", "plant_id": "plant1", "role": "ADMIN"})
    payload = {"executive": {"plant_situation": "ATTENTION", "plant_health": {"status": "DEGRADED", "score": 72}, "top_equipment_risks": [{"equipment": "PT-303", "priority": 84, "status": "URGENT", "reason": "Verified evidence requires review."}]}}
    response = client.post("/api/management", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["top_priorities"][0]["equipment"] == "PT-303"
    assert data["action_queue"]["action_queue"][0]["approval_required"] is True


def test_human_decision_never_executes():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({"authenticated": True, "username": "phase5-test-admin", "user_id": "u1", "organization_id": "org1", "plant_id": "plant1", "role": "ADMIN"})
    response = client.post("/api/management/decision", json={"action": {"action_id": "A-1", "equipment": "PT-303", "action": "INSPECT"}, "decision": "APPROVE", "reviewer": "HOD"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["approved"] is True
    assert data["executed"] is False
    assert data["safety_boundary"]["automatic_execution"] is False


def test_management_page_exists():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({"authenticated": True, "username": "phase5-test-admin", "user_id": "u1", "organization_id": "org1", "plant_id": "plant1", "role": "ADMIN"})
    response = client.get("/management")
    assert response.status_code == 200
    assert b"HUMAN & MANAGEMENT INTELLIGENCE" in response.data
