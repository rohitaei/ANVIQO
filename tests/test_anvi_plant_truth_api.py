import os

import pytest
from datetime import datetime, timezone

os.environ.setdefault("ANVIQO_SECRET_KEY", "ci-only-not-a-real-secret")
os.environ.setdefault("ANVIQO_ADMIN_USER", "ci-only-admin")
os.environ.setdefault("ANVIQO_ADMIN_PASSWORD", "ci-only-password")

import anviqo_api
import anvi_universal_command_centre as adapter



@pytest.fixture(autouse=True)
def _allow_test_tenant_permissions(monkeypatch):
    import anviqo_api_phase2
    import anvi_tenant_store
    allow = lambda *args, **kwargs: True
    monkeypatch.setattr(anviqo_api_phase2, "authorize", allow)
    monkeypatch.setattr(anvi_tenant_store, "authorize", allow)

def _snapshot():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "plant_id": "plant-test",
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
        "timestamp": now,
        "total_io": 4,
        "healthy": 2,
        "warning": 1,
        "critical": 1,
        "changed": 1,
        "active_events": 2,
        "plant_health_score": 62.5,
        "points": [
            {"tag": "PT-201", "state": "HEALTHY", "changed": False, "event_active": False},
            {"tag": "PT-202", "state": "HEALTHY", "changed": True, "event_active": False},
            {"tag": "PT-303", "state": "WARNING", "changed": False, "event_active": True},
            {"tag": "PT-304", "state": "CRITICAL", "changed": False, "event_active": True},
        ],
    }


def _client():
    client = anviqo_api.app.test_client()
    with client.session_transaction() as state:
        state["authenticated"] = True
        state["user_id"] = "user-test"
        state["organization_id"] = "org-test"
        state["plant_id"] = "plant-test"
        state["plant_slug"] = "primary-plant"
        state["username"] = "test-user"
        state["role"] = "ADMIN"
    return client


def test_ask_plant_health_uses_one_reconciled_selected_plant_snapshot(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: _snapshot())
    response = _client().post("/api/ask", json={"question": "What is the current plant health?"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["domain"] == "plant_truth"
    assert data["plant_health_score"] == 62.5
    assert data["evidence_assurance"]["assurance_status"] == "CONSISTENT_SIMULATION_EVIDENCE"
    assert data["plc_write"] is False


def test_ask_alarm_and_critical_equipment_answers_use_same_point_evidence(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: _snapshot())
    client = _client()
    alarms = client.post("/api/ask", json={"question": "Show active alarms"}).get_json()
    critical = client.post("/api/ask", json={"question": "Show critical equipment"}).get_json()
    changed = client.post("/api/ask", json={"question": "What changed?"}).get_json()
    assert alarms["matched_count"] == 2
    assert critical["matched_count"] == 1
    assert changed["matched_count"] == 1
    assert "PT-202" in changed["answer"]
    assert "PT-304" in critical["answer"]


def test_no_selected_plant_data_never_falls_back_to_demo_snapshot(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: None)
    response = _client().post("/api/ask", json={"question": "What is the current plant health?"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["evidence_status"] == "NO_POINT_EVIDENCE"
    assert "did not substitute another plant" in data["answer"]


def test_evidence_assurance_and_decision_brief_api_are_authenticated_and_scoped(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: _snapshot())
    client = _client()
    assurance = client.get("/api/intelligence/evidence-assurance").get_json()
    brief = client.get("/api/intelligence/equipment/PT-304/decision-brief").get_json()
    assert assurance["assurance_status"] == "CONSISTENT_SIMULATION_EVIDENCE"
    assert assurance["scope"] == "SELECTED_PLANT_ONLY"
    assert brief["status"] == "BRIEF_READY"
    assert brief["equipment"]["tag"] == "PT-304"
    assert brief["scope"] == "SELECTED_PLANT_ONLY"
    assert brief["automatic_execution"] is False
