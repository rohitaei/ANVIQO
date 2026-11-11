import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask

import anvi_plc_gateway


def _db(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE anviqo_plants (
        organization_id TEXT, plant_id TEXT, status TEXT)""")
    conn.execute("INSERT INTO anviqo_plants VALUES('org-test','plant-test','ACTIVE')")
    conn.commit()
    conn.close()


def test_gateway_ingest_and_tenant_read(tmp_path, monkeypatch):
    db = tmp_path / "tenant.db"
    _db(db)
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", "sqlite:///" + str(db))
    monkeypatch.setenv("ANVIQO_PLC_INGEST_ORG_ID", "org-test")
    monkeypatch.setenv("ANVIQO_PLC_INGEST_PLANT_ID", "plant-test")
    monkeypatch.setenv("ANVIQO_PLC_INGEST_TOKEN", "x" * 48)
    monkeypatch.setenv("ANVIQO_PLC_ALLOWED_TAGS", "PT_303")

    app = Flask(__name__)
    app.secret_key = "test-secret"
    anvi_plc_gateway.register(app)
    client = app.test_client()
    payload = {"gateway_id": "test-edge", "points": [{
        "tag": "PT_303", "value": 68.0, "unit": "mmWC", "quality": "GOOD",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }]}
    response = client.post("/api/gateway/v1/telemetry", json=payload,
        headers={"Authorization": "Bearer " + "x" * 48})
    assert response.status_code == 202
    assert response.get_json()["accepted"] == 1

    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["organization_id"] = "org-test"
        sess["plant_id"] = "plant-test"
    live = client.get("/api/plc/live")
    assert live.status_code == 200
    data = live.get_json()
    assert data["status"] == "LIVE"
    assert data["points"][0]["tag"] == "PT_303"
    assert data["points"][0]["value"] == 68.0
    assert data["plc_write"] is False
    assert data["scada_control"] is False


def test_gateway_rejects_wrong_token_and_unapproved_tag(tmp_path, monkeypatch):
    db = tmp_path / "tenant.db"
    _db(db)
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", "sqlite:///" + str(db))
    monkeypatch.setenv("ANVIQO_PLC_INGEST_ORG_ID", "org-test")
    monkeypatch.setenv("ANVIQO_PLC_INGEST_PLANT_ID", "plant-test")
    monkeypatch.setenv("ANVIQO_PLC_INGEST_TOKEN", "x" * 48)
    monkeypatch.setenv("ANVIQO_PLC_ALLOWED_TAGS", "PT_303")
    app = Flask(__name__)
    app.secret_key = "test-secret"
    anvi_plc_gateway.register(app)
    client = app.test_client()
    assert client.post("/api/gateway/v1/telemetry", json={},
        headers={"Authorization": "Bearer wrong"}).status_code == 401
    payload = {"gateway_id": "test-edge", "points": [{
        "tag": "NOT_APPROVED", "value": 1, "unit": "", "quality": "GOOD",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }]}
    response = client.post("/api/gateway/v1/telemetry", json=payload,
        headers={"Authorization": "Bearer " + "x" * 48})
    assert response.status_code == 400
