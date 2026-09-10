import os

_APP = None


def _load_app(tmp_path):
    global _APP
    if _APP is not None:
        return _APP
    db = tmp_path / "tenant_v5.sqlite"
    os.environ["ANVIQO_TENANT_DB"] = str(db)
    os.environ["ANVIQO_SECRET_KEY"] = "test-secret-v5"
    os.environ["ANVIQO_ADMIN_USER"] = "admin"
    os.environ["ANVIQO_ADMIN_PASSWORD"] = "password"
    import phase6_enterprise_runtime
    import phase6_enterprise_command_centre_v2  # noqa: F401
    import phase6_enterprise_command_centre_v3  # noqa: F401
    import phase6_enterprise_command_centre_v4  # noqa: F401
    import phase6_enterprise_context_v5  # noqa: F401
    _APP = phase6_enterprise_runtime.app
    return _APP


def _session(client, org="org-1", plant="plant-1", role="ADMIN"):
    with client.session_transaction() as s:
        s["authenticated"] = True
        s["user_id"] = "user-1"
        s["username"] = "admin"
        s["organization_id"] = org
        s["plant_id"] = plant
        s["role"] = role


def test_context_envelope_is_tenant_and_plant_scoped(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _session(client, org="org-1", plant="plant-2")
    r = client.get("/api/enterprise/context-envelope?surface=chat")
    assert r.status_code == 200
    data = r.get_json()
    assert data["context"]["organization_id"] == "org-1"
    assert data["context"]["active_plant_id"] == "plant-2"
    assert data["context"]["surface"] == "chat"
    assert data["context"]["evidence_policy"] == "existing_evidence_only"
    assert r.headers["X-ANVIQO-Active-Plant"] == "plant-2"


def test_context_check_prevents_false_plant_attribution(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _session(client, plant="plant-2")
    r = client.post("/api/enterprise/context-check", json={"plant_id": "plant-1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["matches_active_context"] is False
    assert data["safe_to_attribute"] is False


def test_context_check_accepts_active_plant(tmp_path):
    app = _load_app(tmp_path)
    client = app.test_client()
    _session(client, plant="plant-2")
    r = client.post("/api/enterprise/context-check", json={"plant_id": "plant-2"})
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
    _session(client)
    data = client.get("/api/enterprise/context-envelope?surface=plant_health").get_json()["context"]["governance"]
    assert data["plc_write"] is False
    assert data["scada_control"] is False
    assert data["automatic_authorization"] is False
    assert data["automatic_execution"] is False
    assert data["human_decision_required"] is True
