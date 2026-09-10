import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "phase6v3.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "phase6-v3-admin")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "phase6-v3-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "phase6-v3-secret")
    import phase6_enterprise_command_centre_v3  # noqa: F401
    from phase5_command_centre_runtime import app
    app.config.update(TESTING=True, SECRET_KEY="phase6-v3-secret")
    with app.test_client() as c:
        yield c


def login(c):
    r = c.post("/login", data={"username": "phase6-v3-admin", "password": "phase6-v3-password"}, follow_redirects=True)
    assert r.status_code < 500


def test_portfolio_requires_auth(client):
    assert client.get("/api/enterprise/portfolio").status_code == 401


def test_portfolio_is_tenant_scoped_and_evidence_honest(client):
    login(client)
    r = client.get("/api/enterprise/portfolio")
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "OK"
    assert d["plant_count"] == len(d["plants"])
    assert d["organization_id"]
    assert d["governance"]["plc_write"] is False
    assert d["governance"]["scada_control"] is False
    for plant in d["plants"]:
        if plant["plant_id"] != d["active_plant_id"]:
            assert plant["evidence"]["evidence_status"] == "NOT_EVALUATED"


def test_portfolio_has_no_control_enablement():
    source = open("phase6_enterprise_command_centre_v3.py", encoding="utf-8").read().lower()
    assert "plc_write = true" not in source
    assert "scada_control = true" not in source
    assert "automatic_execution = true" not in source
