import os
from pathlib import Path

os.environ.setdefault("ANVIQO_SECRET_KEY", "phase5-live-test-secret")
os.environ.setdefault("ANVIQO_ADMIN_USER", "phase5-live-test-admin")
os.environ.setdefault("ANVIQO_ADMIN_PASSWORD", "phase5-live-test-password")
_TEST_DB = Path("/tmp/anviqo_phase5_live_test.db")
_TEST_DB.unlink(missing_ok=True)
os.environ["ANVIQO_TENANT_DB_URL"] = f"sqlite://{_TEST_DB}"

import phase5_command_centre_runtime as runtime


def _login(client):
    return client.post("/login", data={"username": os.environ["ANVIQO_ADMIN_USER"], "password": os.environ["ANVIQO_ADMIN_PASSWORD"]}, follow_redirects=False)


def test_hod_get_uses_existing_evidence_adapter():
    client = runtime.app.test_client()
    assert _login(client).status_code == 302
    response = client.get("/api/hod-management")
    assert response.status_code == 200
    data = response.get_json()
    assert "evidence_context" in data
    assert "areas" in data
    assert data["safety_boundary"]["plc_write"] is False
    assert data["safety_boundary"]["scada_control"] is False


def test_hod_page_still_available():
    client = runtime.app.test_client()
    _login(client)
    response = client.get("/management")
    assert response.status_code == 200
    assert b"AREA HEALTH" in response.data
