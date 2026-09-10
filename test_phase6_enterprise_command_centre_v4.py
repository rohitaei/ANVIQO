import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "phase6_v4.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "phase6-v4-admin")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "phase6-v4-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "phase6-v4-secret")

    import phase6_enterprise_runtime_v4  # noqa: F401
    from phase6_enterprise_runtime_v4 import app
    app.config.update(TESTING=True, SECRET_KEY="phase6-v4-secret", SESSION_COOKIE_SECURE=False)
    with app.test_client() as c:
        yield c


def _login(c):
    return c.post(
        "/login",
        data={"username": "phase6-v4-admin", "password": "phase6-v4-password"},
        follow_redirects=True,
    )


def test_unauthenticated_context_switch_is_blocked(client):
    r = client.post("/api/enterprise/select-plant", json={"plant_id": "plant_missing"})
    assert r.status_code == 401


def test_admin_can_switch_only_within_active_organization(client):
    assert _login(client).status_code < 500
    import anvi_tenant_store as store
    context = client.get("/api/enterprise/context").get_json()
    org_id = context["organization"]["organization_id"]
    current = context["active_plant_id"]
    second = store.create_plant(org_id, "PCI Demonstration Plant", "pci-demo-v4")
    r = client.post("/api/enterprise/select-plant", json={"plant_id": second})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "SWITCHED"
    assert data["active_plant_id"] == second
    assert data["previous_plant_id"] == current
    assert data["governance"]["plc_write"] is False
    assert data["governance"]["scada_control"] is False
    assert data["governance"]["automatic_execution"] is False
    active = client.get("/api/enterprise/active-context")
    assert active.status_code == 200
    assert active.get_json()["active_plant_id"] == second


def test_cross_organization_selection_is_forbidden(client):
    assert _login(client).status_code < 500
    import anvi_tenant_store as store
    other_org = store.create_organization("Other Org", "other-org-v4")
    other_plant = store.create_plant(other_org, "Other Plant", "other-plant-v4")
    r = client.post("/api/enterprise/select-plant", json={"plant_id": other_plant})
    assert r.status_code == 403
    assert r.get_json()["switched"] is False


def test_non_admin_can_switch_to_a_plant_they_can_read(client):
    assert _login(client).status_code < 500
    import anvi_tenant_store as store
    context = client.get("/api/enterprise/context").get_json()
    org_id = context["organization"]["organization_id"]
    first = context["active_plant_id"]
    second = store.create_plant(org_id, "Operator Plant", "operator-plant-v4")
    user_id = store.create_user("phase6-v4-operator", "Phase 6 V4 Operator")
    store.create_membership(user_id, org_id, second, "OPERATOR")
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_id"] = user_id
        sess["username"] = "phase6-v4-operator"
        sess["organization_id"] = org_id
        sess["plant_id"] = first
        sess["role"] = "OPERATOR"
    r = client.post("/api/enterprise/select-plant", json={"plant_id": second})
    assert r.status_code == 200
    assert r.get_json()["active_plant_id"] == second


def test_portfolio_follows_selected_context_without_fabricating_other_plants(client):
    assert _login(client).status_code < 500
    import anvi_tenant_store as store
    context = client.get("/api/enterprise/context").get_json()
    org_id = context["organization"]["organization_id"]
    second = store.create_plant(org_id, "Portfolio Plant", "portfolio-plant-v4")
    assert client.post("/api/enterprise/select-plant", json={"plant_id": second}).status_code == 200
    data = client.get("/api/enterprise/portfolio").get_json()
    assert data["active_plant_id"] == second
    selected = next(p for p in data["plants"] if p["plant_id"] == second)
    assert selected["intelligence_scope"] == "ACTIVE_CONTEXT"
    assert data["governance"]["plc_write"] is False
    assert data["governance"]["scada_control"] is False


def test_v4_source_contains_no_enabled_control_flags():
    for path in ("phase6_enterprise_command_centre_v4.py", "phase6_enterprise_runtime_v4.py"):
        source = open(path, encoding="utf-8").read().lower()
        assert "plc_write = true" not in source
        assert "scada_control = true" not in source
        assert "automatic_execution = true" not in source
