import importlib
import sys
from types import SimpleNamespace

from flask import Flask


def _load_bridge(monkeypatch):
    app = Flask("field_report_bridge_test")
    app.secret_key = "qa-only"
    monkeypatch.setitem(sys.modules, "anviqo_api_phase2", SimpleNamespace(app=app))
    sys.modules.pop("field_report_persistent_bridge", None)
    bridge = importlib.import_module("field_report_persistent_bridge")
    return app, bridge


def test_report_history_query_never_falls_through_when_report_missing(monkeypatch):
    app, bridge = _load_bridge(monkeypatch)
    monkeypatch.setattr(bridge, "_field_reports_from_neon", lambda tag="", limit=20: [])

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "QA-USER"
            sess["organization_id"] = "QA-ORG"
            sess["plant_id"] = "QA-PLANT"
        response = client.post(
            "/api/ask",
            json={"question": "Show the saved field report for PT_303. Include observation and outcome."},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "NOT_FOUND"
    assert payload["requested_tag"] == "PT-303"
    assert "No saved technician field report" in payload["answer"]
    assert payload["evidence"] is None
    assert payload["plc_write"] is False
    assert payload["scada_control"] is False


def test_report_history_query_reports_store_failure_not_false_not_found(monkeypatch):
    app, bridge = _load_bridge(monkeypatch)

    def unavailable(tag="", limit=20):
        raise RuntimeError("private database detail")

    monkeypatch.setattr(bridge, "_field_reports_from_neon", unavailable)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "QA-USER"
            sess["organization_id"] = "QA-ORG"
            sess["plant_id"] = "QA-PLANT"
        response = client.post(
            "/api/ask",
            json={"question": "Show the saved field report for PT_303."},
        )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "LOOKUP_UNAVAILABLE"
    assert "couldn't verify the saved field report" in payload["answer"]
    assert "private database detail" not in response.get_data(as_text=True)
