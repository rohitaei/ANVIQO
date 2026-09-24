import pytest

from anviqo_api_phase2 import app
import failure_prediction_api as api


def _authenticated_context(question="predict PT-303"):
    return app.test_request_context(
        "/api/ask",
        method="POST",
        json={"question": question, "observations": []},
    )


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
        with _authenticated_context():
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert captured["plant_id"] == "PLANT-A"
    assert captured["organization_id"] == "ORG-1"
    assert captured["tag"] == "PT-303"
    assert result["failure_prediction"]["execution_audit"]["plant_id"] == "PLANT-A"
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["human_decision_required"] is True


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
        with _authenticated_context():
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert result[0]["status"] == "TENANT_CONTEXT_REQUIRED"
    assert result[1] == 409


def test_alpha22_api_ask_blocks_cross_organization_plant_before_predictor(monkeypatch):
    called = {"flow": False}

    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {
        "user_id": "U2",
        "organization_id": "ORG-OTHER",
        "plant_id": "PLANT-A",
        "role": "operator",
        "username": "cross-org-test",
    })

    import failure_prediction
    monkeypatch.setattr(failure_prediction, "is_failure_prediction_query", lambda question: True)
    monkeypatch.setattr(failure_prediction, "extract_tag", lambda question: "PT-303")
    monkeypatch.setattr(failure_prediction, "build_failure_prediction", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy predictor must not be called")))

    def forbidden_flow(**kwargs):
        called["flow"] = True
        raise AssertionError("predictive flow must not run for an unauthorized organization/plant")

    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)
    monkeypatch.setattr("v3.production_boundary.run_production_predictive_flow", forbidden_flow)

    old_secret = app.secret_key
    app.secret_key = "alpha22-test"
    try:
        with _authenticated_context():
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert called["flow"] is False
    assert result[0]["status"] == "FORBIDDEN"
    assert result[1] == 403
    assert result[0]["read_only"] is True
    assert result[0]["plc_write"] is False
    assert result[0]["scada_control"] is False


def test_alpha21_predictive_api_route_exists_and_is_read_only_contract():
    assert api.failure_prediction_api is not None
    assert api.failure_prediction_query_bridge is not None
