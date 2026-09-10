import os

_APP = None


def _load_app(tmp_path):
    global _APP
    if _APP is not None:
        return _APP
    db = tmp_path / "tenant_v5.sqlite"
    os.environ["ANVIQO_TENANT_DB_URL"] = f"sqlite:///{db}"
    os.environ["ANVIQO_ADMIN_USER"] = "phase6-v5-admin"
    os.environ["ANVIQO_ADMIN_PASSWORD"] = "phase6-v5-password"
    os.environ["ANVIQO_SECRET_KEY"] = "test-secret-v5"
    import phase6_enterprise_runtime
    import phase6_enterprise_command_centre_v2  # noqa: F401
    import phase6_enterprise_command_centre_v3  # noqa: F401
    import phase6_enterprise_command_centre_v4  # noqa: F401
    import phase6_enterprise_context_v5  # noqa: F401
    _APP = phase6_enterprise_runtime.app
    _APP.config.update(TESTING=True, SECRET_KEY="test-secret-v5", SESSION_COOKIE_SECURE=False)
    return _APP


def _login(client):
    r = client.post(
        "/login",
        data={"username": "phase6-v5-admin", "password": "phase6-v5-password"},
        follow_redirects=True,
    )
    assert r.status_code < 500
    return r


def test_context_envelope_is_tenant_and_plant_scoped(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _login(client)
    base = client.get("/api/enterprise/context")
    assert base.status_code == 200
    base_data = base.get_json()
    r = client.get("/api/enterprise/context-envelope?surface=chat")
    assert r.status_code == 200
    data = r.get_json()
    assert data["context"]["organization_id"] == base_data["organization"]["organization_id"]
    assert data["context"]["active_plant_id"] == base_data["active_plant_id"]
    assert data["context"]["surface"] == "chat"
    assert data["context"]["evidence_policy"] == "existing_evidence_only"
    assert r.headers["X-ANVIQO-Active-Plant"] == base_data["active_plant_id"]


def test_context_check_prevents_false_plant_attribution(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _login(client)
    active = client.get("/api/enterprise/context").get_json()["active_plant_id"]
    requested = "plant_that_is_not_active_for_v5_test"
    assert requested != active
    r = client.post("/api/enterprise/context-check", json={"plant_id": requested})
    assert r.status_code == 200
    data = r.get_json()
    assert data["matches_active_context"] is False
    assert data["safe_to_attribute"] is False


def test_context_check_accepts_active_plant(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _login(client)
    active = client.get("/api/enterprise/context").get_json()["active_plant_id"]
    r = client.post("/api/enterprise/context-check", json={"plant_id": active})
    assert r.status_code == 200
    assert r.get_json()["safe_to_attribute"] is True


def test_unauthenticated_context_blocked(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    with client.session_transaction() as s:
        s.clear()
    r = client.get("/api/enterprise/context-envelope?surface=reports")
    assert r.status_code == 401


def test_safety_contract_has_no_control_enablement(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _login(client)
    data = client.get("/api/enterprise/context-envelope?surface=plant_health").get_json()["context"]["governance"]
    assert data["plc_write"] is False
    assert data["scada_control"] is False
    assert data["automatic_authorization"] is False
    assert data["automatic_execution"] is False
    assert data["human_decision_required"] is True
