import pytest

from anviqo_api_phase2 import app
import failure_prediction_api as api


def _authenticated_context(question="predict PT-303", path="/api/ask", payload=None):
    body = payload or {"question": question, "observations": []}
    return app.test_request_context(path, method="POST", json=body)


def test_alpha21_api_ask_uses_v3_tenant_flow(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {"user_id": "U1", "organization_id": "ORG-1", "plant_id": "PLANT-A", "role": "operator", "username": "test"})
    import failure_prediction
    monkeypatch.setattr(failure_prediction, "is_failure_prediction_query", lambda question: True)
    monkeypatch.setattr(failure_prediction, "build_failure_prediction", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy predictor must not be called")))
    monkeypatch.setattr(failure_prediction, "extract_tag", lambda question: "PT-303")

    def fake_flow(**kwargs):
        captured.update(kwargs)
        return {
            "plant_id": "PLANT-A",
            "tag": "PT-303",
            "evidence": {"quality": "VALID", "usable_observation_count": 2, "window_start": "2026-09-20T10:00:00Z", "window_end": "2026-09-20T10:01:00Z"},
            "prediction": {"status": "INVOKED", "reason": "tenant-safe predictor invoked"},
            "execution_audit": {"plant_id": "PLANT-A", "tag": "PT-303", "evidence_quality": "VALID"},
        }

    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)
    monkeypatch.setattr("v3.production_boundary.run_production_predictive_flow", fake_flow)
    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)
    old_secret = app.secret_key
    app.secret_key = "alpha23-test"
    try:
        with _authenticated_context():
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret

    assert captured["plant_id"] == "PLANT-A"
    assert captured["organization_id"] == "ORG-1"
    assert result["failure_prediction"]["evidence"]["quality"] == "VALID"
    assert result["failure_prediction"]["evidence"]["usable_observation_count"] == 2
    assert result["failure_prediction"]["evidence"]["window_start"] == "2026-09-20T10:00:00Z"
    assert result["failure_prediction"]["execution_audit"]["evidence_quality"] == "VALID"
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["human_decision_required"] is True


def test_alpha21_api_ask_blocks_missing_tenant_context(monkeypatch):
    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {"user_id": "U1", "organization_id": "", "plant_id": "", "role": "operator", "username": "test"})
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
    predictor_called = {"value": False}
    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {"user_id": "U2", "organization_id": "ORG-OTHER", "plant_id": "PLANT-A", "role": "operator", "username": "cross-org-test"})
    import failure_prediction
    monkeypatch.setattr(failure_prediction, "is_failure_prediction_query", lambda question: True)
    monkeypatch.setattr(failure_prediction, "extract_tag", lambda question: "PT-303")
    monkeypatch.setattr(failure_prediction, "build_failure_prediction", lambda *args, **kwargs: predictor_called.__setitem__("value", True))
    monkeypatch.setattr("v3.production_boundary.run_production_predictive_flow", lambda **kwargs: (_ for _ in ()).throw(PermissionError("Plant is not authorized for this organization")))
    monkeypatch.setattr(api, "jsonify", lambda value, status_code=None: (value, status_code) if status_code else value)
    old_secret = app.secret_key
    app.secret_key = "alpha22-test"
    try:
        with _authenticated_context():
            api.session["authenticated"] = True
            result = api.failure_prediction_query_bridge()
    finally:
        app.secret_key = old_secret
    assert result[0]["status"] == "FORBIDDEN"
    assert result[1] == 403
    assert predictor_called["value"] is False


def test_alpha23_failure_prediction_api_preserves_provenance(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "_can_read", lambda actor: True)
    monkeypatch.setattr(api, "_actor", lambda: {"user_id": "U1", "organization_id": "ORG-1", "plant_id": "PLANT-A", "role": "operator", "username": "test"})
    import failure_prediction
    monkeypatch.setattr(failure_prediction, "extract_tag", lambda query: "PT-303")

    expected = {
        "plant_id": "PLANT-A",
        "tag": "PT-303",
        "evidence": {"quality": "VALID", "usable_observation_count": 2, "window_start": "2026-09-20T10:00:00Z", "window_end": "2026-09-20T10:01:00Z"},
        "prediction": {"status": "INVOKED", "reason": "existing predictor invoked"},
        "execution_audit": {"plant_id": "PLANT-A", "tag": "PT-303", "evidence_quality": "VALID"},
    }

    def fake_flow(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr("v3.production_boundary.run_production_predictive_flow", fake_flow)
    old_secret = app.secret_key
    app.secret_key = "alpha23-test"
    try:
        with _authenticated_context(
            path="/api/failure_prediction",
            payload={
                "query": "predict PT-303",
                "observations": [
                    {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 1.0},
                    {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 1.1},
                ],
                "window_start": "2026-09-20T10:00:00Z",
                "window_end": "2026-09-20T10:01:00Z",
            },
        ):
            api.session["authenticated"] = True
            result = api.failure_prediction_api()
    finally:
        app.secret_key = old_secret

    assert captured["plant_id"] == "PLANT-A"
    assert captured["organization_id"] == "ORG-1"
    assert captured["tag"] == "PT-303"
    assert captured["window_start"] == "2026-09-20T10:00:00Z"
    assert captured["window_end"] == "2026-09-20T10:01:00Z"
    assert result["failure_prediction"]["evidence"]["quality"] == "VALID"
    assert result["failure_prediction"]["evidence"]["window_end"] == "2026-09-20T10:01:00Z"
    assert result["failure_prediction"]["execution_audit"]["tag"] == "PT-303"
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["human_decision_required"] is True


def test_alpha21_predictive_api_route_exists_and_is_read_only_contract():
    assert api.failure_prediction_api is not None
    assert api.failure_prediction_query_bridge is not None
