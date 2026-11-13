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
        "total_io": 2,
        "healthy": 1,
        "warning": 1,
        "critical": 0,
        "changed": 0,
        "active_events": 0,
        "plant_health_score": 75.0,
        "points": [
            {"tag": "PT-303", "name": "Mill outlet gas pressure", "area": "VRM/MILL",
             "value": 68.0, "state": "WARNING", "changed": False, "event_active": False,
             "mode": "SIMULATION", "source": "PCI DEMO STREAM"},
            {"tag": "PT-304", "name": "Bag filter inlet pressure", "area": "BAG FILTER",
             "value": 42.0, "state": "HEALTHY", "changed": False, "event_active": False,
             "mode": "SIMULATION", "source": "PCI DEMO STREAM"},
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


def test_conversational_decision_brief_returns_selected_plant_evidence(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: _snapshot())
    response = _client().post("/api/ask", json={"question": "Prepare an equipment decision brief for PT-303"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "BRIEF_READY"
    assert data["equipment"]["tag"] == "PT-303"
    assert data["decision_priority"] == "P2_ENGINEERING_REVIEW"
    assert data["evidence_quality"] == "SIMULATION_ONLY_NOT_LIVE_TELEMETRY"
    assert data["scope"] == "SELECTED_PLANT_ONLY"
    assert data["plc_write"] is False and data["scada_control"] is False
    assert "No physical root cause" in data["answer"]


def test_conversational_decision_brief_requires_exact_tag(monkeypatch):
    response = _client().post("/api/ask", json={"question": "Prepare an equipment decision brief"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["evidence_status"] == "EXACT_EQUIPMENT_TAG_REQUIRED"


def test_conversational_decision_brief_does_not_fall_back_to_another_tag(monkeypatch):
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: _snapshot())
    response = _client().post("/api/ask", json={"question": "Prepare an equipment decision brief for PT-519"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "EQUIPMENT_NOT_FOUND"
    assert data.get("equipment") in (None, {})
    assert data["scope"] == "SELECTED_PLANT_ONLY"



def test_conversational_brief_ignores_same_tag_spare_inventory_row(monkeypatch):
    snapshot = _snapshot()
    snapshot["points"].append({
        "tag": "PT-303",
        "name": "PCI_PT 3051L5A-0.15-0Kg/cm²",
        "record_type": "CRITICAL_SPARE",
        "asset_type": "CRITICAL_SPARE",
        "state": "WARNING",
        "value": 9,
        "mode": "SIMULATION",
        "source": "critical_spares.xlsx",
    })
    monkeypatch.setattr(adapter, "_tenant_snapshot", lambda plant_id: snapshot)
    response = _client().post(
        "/api/ask",
        json={"question": "Prepare an equipment decision brief for PT-303"},
    )
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "BRIEF_READY"
    assert data["equipment"]["tag"] == "PT-303"
    assert data["excluded_inventory_match_count"] == 1
    assert "Observed state: WARNING" in data["answer"]
