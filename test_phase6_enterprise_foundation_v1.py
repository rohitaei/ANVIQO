import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "phase6.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "phase6-admin")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "phase6-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "phase6-secret")

    import phase6_enterprise_runtime  # noqa: F401
    from phase5_command_centre_runtime import app
    app.config.update(TESTING=True, SECRET_KEY="phase6-secret")
    with app.test_client() as c:
        yield c


def _login(c):
    r = c.post("/login", data={"username": "phase6-admin", "password": "phase6-password"}, follow_redirects=True)
    assert r.status_code < 500
    return r


def test_enterprise_context_is_tenant_scoped(client):
    _login(client)
    r = client.get("/api/enterprise/context")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "OK"
    assert data["organization"]["slug"] == "anviqo-customer"
    assert len(data["plants"]) >= 1
    assert data["governance"]["plc_write"] is False
    assert data["governance"]["scada_control"] is False


def test_admin_can_add_second_plant(client):
    _login(client)
    r = client.post("/api/enterprise/plants", json={"name": "PCI Demonstration Plant", "slug": "pci-demo"})
    assert r.status_code == 201
    plant_id = r.get_json()["plant_id"]
    assert plant_id.startswith("plant_")
    r = client.get(f"/api/enterprise/plant/{plant_id}")
    assert r.status_code == 200
    assert r.get_json()["plant"]["slug"] == "pci-demo"


def test_cross_organization_plant_is_forbidden(client):
    _login(client)
    import anvi_tenant_store as store
    other_org = store.create_organization("Other Org", "other-org")
    other_plant = store.create_plant(other_org, "Other Plant", "other-plant")
    r = client.get(f"/api/enterprise/plant/{other_plant}")
    assert r.status_code == 403


def test_unauthenticated_is_blocked(client):
    r = client.get("/api/enterprise/context")
    assert r.status_code == 401


def test_no_control_enablement_in_enterprise_runtime():
    source = open("phase6_enterprise_runtime.py", encoding="utf-8").read().lower()
    assert "plc_write = true" not in source
    assert "scada_control = true" not in source
    assert "automatic_execution = true" not in source
