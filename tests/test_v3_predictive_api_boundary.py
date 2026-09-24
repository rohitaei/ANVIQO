import pytest

from anviqo_api_phase2 import app
import failure_prediction_api as api


def test_alpha21_api_ask_uses_v3_tenant_flow(monkeypatch):
    captured = {}

    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {
        "user_id": "U1",
        "organization_id": "ORG-1",
        "plant_id": "PLANT-A",
        "role": "operator",
        "username": "test",
    })

    import failure_prediction
    monkeypatch.setattr(failure_prediction, "is_failure_prediction_query", lambda question: True)
    monkeypatch.setattr(failure_prediction, "build_failure_prediction", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy predictor must not be called")))
    monkeypatch.setattr(failure_prediction, "extract_tag", lambda question: "PT-303")

    def fake_flow(**kwargs):
        captured.update(kwargs)
        return {
            "plant_id": "PLANT-A",
            "tag": "PT-303",
            "prediction": {"status": "INVOKED", "reason": "tenant-safe predictor invoked"},
            "execution_audit": {"plant_id": "PLANT-A", "tag": "PT-303"},
        }

    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)
    monkeypatch.setattr("v3.production_boundary.run_production_predictive_flow", fake_flow)

    old_secret = app.secret_key
    app.secret_key = "alpha21-test"
    try:
        with app.test_request_context("/api/ask", method="POST", json={"question": "predict PT-303", "observations": []}):
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert captured["plant_id"] == "PLANT-A"
    assert captured["organization_id"] == "ORG-1"
    assert captured["tag"] == "PT-303"
    assert result["failure_prediction"]["execution_audit"]["plant_id"] == "PLANT-A"


def test_alpha21_api_ask_blocks_missing_tenant_context(monkeypatch):
    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {
        "user_id": "U1",
        "organization_id": "",
        "plant_id": "",
        "role": "operator",
        "username": "test",
    })

    import failure_prediction
    monkeypatch.setattr(failure_prediction, "is_failure_prediction_query", lambda question: True)
    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)

    old_secret = app.secret_key
    app.secret_key = "alpha21-test"
    try:
        with app.test_request_context("/api/ask", method="POST", json={"question": "predict PT-303"}):
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert result[0]["status"] == "TENANT_CONTEXT_REQUIRED"
    assert result[1] == 409


def test_alpha21_predictive_api_safety_is_read_only():
    assert api._run_tenant_predictive_request is not None
    assert api.failure_prediction_api is not None
