import json
from flask import Flask, session
import anvi_neon_store


def test_generated_report_id_is_stable_and_embedded(monkeypatch):
    saved = {}
    app = Flask(__name__)
    app.secret_key = "qa-only"

    def fake_exec(sql, params=(), fetch=False):
        if "INSERT INTO anviqo_field_reports" in sql:
            saved[str(params[0])] = json.loads(params[3])
        return [] if fetch else None

    monkeypatch.setattr(anvi_neon_store, "neon_enabled", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "init_neon", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)
    report = {
        "source": "technician field report",
        "tag": "PT_303",
        "observation": "QA observation",
        "maintenance_action": "QA action",
    }

    with app.test_request_context("/api/field_report", method="POST"):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        session["plant_id"] = "QA-PLANT-ONLY"
        assert anvi_neon_store.upsert_field_report(report) is True
        first_id = next(iter(saved))
        assert saved[first_id]["report_id"] == first_id
        assert anvi_neon_store.upsert_field_report(report) is True
        assert len(saved) == 1
        assert next(iter(saved)) == first_id


def test_session_tenant_overrides_payload_tenant(monkeypatch):
    saved = {}
    app = Flask(__name__)
    app.secret_key = "qa-only"

    def fake_exec(sql, params=(), fetch=False):
        if "INSERT INTO anviqo_field_reports" in sql:
            saved[str(params[0])] = json.loads(params[3])
        return [] if fetch else None

    monkeypatch.setattr(anvi_neon_store, "neon_enabled", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "init_neon", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)

    with app.test_request_context("/api/field_report", method="POST"):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        session["plant_id"] = "QA-PLANT-ONLY"
        assert anvi_neon_store.upsert_field_report({
            "report_id": "QA-FR-TENANT",
            "tag": "PT-303",
            "organization_id": "UNTRUSTED-ORG",
            "plant_id": "UNTRUSTED-PLANT",
            "observation": "QA only",
        }) is True

    assert saved["QA-FR-TENANT"]["organization_id"] == "QA-ORG-ONLY"
    assert saved["QA-FR-TENANT"]["plant_id"] == "QA-PLANT-ONLY"


def test_storage_rejects_authenticated_request_without_selected_plant(monkeypatch):
    writes = []
    app = Flask(__name__)
    app.secret_key = "qa-only"

    def fake_exec(sql, params=(), fetch=False):
        if "INSERT INTO anviqo_field_reports" in sql:
            writes.append(params)
        return [] if fetch else None

    monkeypatch.setattr(anvi_neon_store, "neon_enabled", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "init_neon", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)

    with app.test_request_context("/api/field_report", method="POST"):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        assert anvi_neon_store.upsert_field_report({
            "report_id": "QA-FR-NO-PLANT",
            "tag": "PT-303",
            "plant_id": "UNTRUSTED-PLANT",
            "observation": "QA only",
        }) is False

    assert writes == []
