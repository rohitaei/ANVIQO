import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "phase6v2.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "phase6-v2-admin")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "phase6-v2-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "phase6-v2-secret")
    import phase6_enterprise_command_centre_v2  # noqa: F401
    from phase5_command_centre_runtime import app
    app.config.update(TESTING=True, SECRET_KEY="phase6-v2-secret")
    with app.test_client() as c:
        yield c


def login(c):
    r = c.post("/login", data={"username": "phase6-v2-admin", "password": "phase6-v2-password"}, follow_redirects=True)
    assert r.status_code < 500


def test_enterprise_command_centre_is_authenticated(client):
    assert client.get("/api/enterprise/command-centre").status_code == 401
    login(client)
    r = client.get("/api/enterprise/command-centre")
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "OK"
    assert isinstance(d["plants"], list)
    assert d["intelligence_route"] == "/api/hod-management"
    assert d["governance"]["plc_write"] is False
    assert d["governance"]["scada_control"] is False


def test_enterprise_view_exists(client):
    login(client)
    r = client.get("/enterprise")
    assert r.status_code == 200
    assert b"ENTERPRISE COMMAND CENTRE" in r.data


def test_v2_does_not_enable_control():
    source = open("phase6_enterprise_command_centre_v2.py", encoding="utf-8").read().lower()
    assert "plc_write = true" not in source
    assert "scada_control = true" not in source
    assert "automatic_execution = true" not in source
