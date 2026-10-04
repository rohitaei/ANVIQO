import os
import io
import sqlite3
from pathlib import Path


def test_plant_scoped_login_and_isolation(tmp_path, monkeypatch):
    db = tmp_path / "tenant.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "admin-test")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "test-secret")

    import anvi_tenant_store as store
    import anvi_plant_auth as auth
    store.ensure_bootstrap("admin-test")
    org_id = store.create_organization("Test Org", "test-org")
    plant_a = store.create_plant(org_id, "Plant A", "plant-a")
    plant_b = store.create_plant(org_id, "Plant B", "plant-b")
    user = store.create_user("operator-a", "Operator A")
    store.create_membership(user, org_id, plant_a, "OPERATOR")
    auth.set_password("operator-a", "operator-password")

    identity = auth.authenticate("operator-a", "operator-password", "plant-a")
    assert identity and identity["plant_id"] == plant_a
    assert auth.authenticate("operator-a", "operator-password", "plant-b") is None
    assert auth.authenticate("operator-a", "wrong-password", "plant-a") is None

    plants = auth.list_user_plants("operator-a")
    assert [p["plant_id"] for p in plants] == [plant_a]


def test_production_runtime_imports_plant_auth_routes(monkeypatch):
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "admin-test")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "test-secret")
    import phase6_enterprise_runtime_v4 as runtime
    rules = [r for r in runtime.app.url_map.iter_rules()]
    paths = {r.rule for r in rules}
    assert "/api/session/context" in paths
    assert "/api/my-plants" in paths
    assert "/api/admin/plant-users" in paths


def test_authenticated_plant_selection_enforces_scope(monkeypatch):
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "admin-test")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "test-secret")

    import anvi_tenant_store as store
    store.ensure_bootstrap("admin-test")
    org_id = store.create_organization("Selection Org", "selection-org")
    plant_a = store.create_plant(org_id, "Plant A", "plant-a")
    plant_b = store.create_plant(org_id, "Plant B", "plant-b")

    from anvi_plant_auth_routes import app
    client = app.test_client()
    with client.session_transaction() as sess:
        sess.update({
            "authenticated": True,
            "username": "admin-test",
            "user_id": "bootstrap-admin-test",
            "organization_id": org_id,
            "role": "ADMIN",
            "plant_id": plant_a,
        })

    selected = client.post("/api/select-plant", json={"plant_id": plant_b})
    assert selected.status_code == 200
    assert selected.get_json()["plant_id"] == plant_b
    assert selected.get_json()["scope"] == "SELECTED_PLANT_ONLY"

    with client.session_transaction() as sess:
        assert sess["plant_id"] == plant_b

    denied = client.post("/api/select-plant", json={"plant_id": "plant-from-other-org"})
    assert denied.status_code == 403



def test_fresh_plant_knowledge_isolation_after_onboarding(tmp_path, monkeypatch):
    db = tmp_path / "tenant-isolation.db"
    monkeypatch.setenv("ANVIQO_TENANT_DB_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ANVIQO_ADMIN_USER", "admin-test")
    monkeypatch.setenv("ANVIQO_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("ANVIQO_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ANVIQO_SIMULATION_PLANT_SLUG", "primary-plant")

    import anvi_tenant_store as store
    import anvi_plant_auth as auth
    from anvi_plant_auth_routes import app

    store.ensure_bootstrap("admin-test")
    org_a = store.create_organization("Isolation Org A", "isolation-a")
    org_b = store.create_organization("Isolation Org B", "isolation-b")
    plant_a = store.create_plant(org_a, "Alpha Plant", "alpha-plant")
    plant_b = store.create_plant(org_b, "Beta Plant", "beta-plant")
    user_a = store.create_user("operator-alpha", "Operator Alpha")
    user_b = store.create_user("operator-beta", "Operator Beta")
    store.create_membership(user_a, org_a, plant_a, "OPERATOR")
    store.create_membership(user_b, org_b, plant_b, "OPERATOR")
    auth.set_password("operator-alpha", "operator-alpha-password")
    auth.set_password("operator-beta", "operator-beta-password")

    client = app.test_client()

    def sign_in(username, password, plant_slug):
        response = client.post("/login", data={"username": username, "password": password, "plant_slug": plant_slug})
        assert response.status_code in (302, 303)

    # Onboard each plant with deliberately unique engineering identities.
    sign_in("operator-alpha", "operator-alpha-password", "alpha-plant")
    with client.session_transaction() as sess:
        sess["role"] = "ADMIN"
    # The ingestion endpoints are OWNER/ADMIN-only, so use a scoped admin session
    # for each organization rather than granting cross-organization membership.
    with client.session_transaction() as sess:
        sess.update({"authenticated": True, "username": "operator-alpha", "user_id": user_a,
                     "organization_id": org_a, "plant_id": plant_a, "plant_name": "Alpha Plant",
                     "plant_slug": "alpha-plant", "role": "ADMIN"})
    csv_a = b"tag,description,area,service\nAA-1001,Alpha valve pressure,ALPHA,Alpha service\n"
    r = client.post(f"/api/admin/onboarding/plant/{plant_a}/documents", data={"files": (io.BytesIO(csv_a), "alpha.csv")}, content_type="multipart/form-data")
    assert r.status_code == 201
    r = client.post(f"/api/admin/onboarding/plant/{plant_a}/ingest")
    assert r.status_code in (200, 202)

    with client.session_transaction() as sess:
        sess.update({"username": "operator-beta", "user_id": user_b, "organization_id": org_b,
                     "plant_id": plant_b, "plant_name": "Beta Plant", "plant_slug": "beta-plant",
                     "role": "ADMIN"})
    csv_b = b"tag,description,area,service\nBB-2002,Beta fan temperature,BETA,Beta service\n"
    r = client.post(f"/api/admin/onboarding/plant/{plant_b}/documents", data={"files": (io.BytesIO(csv_b), "beta.csv")}, content_type="multipart/form-data")
    assert r.status_code == 201
    r = client.post(f"/api/admin/onboarding/plant/{plant_b}/ingest")
    assert r.status_code in (200, 202)

    # The selected plant can see its own record and cannot see the other plant's record.
    own = client.get("/api/plant/knowledge?q=BB-2002")
    assert own.status_code == 200
    assert own.get_json()["count"] == 1
    assert own.get_json()["records"][0]["tag"] == "BB-2002"
    foreign = client.get("/api/plant/knowledge?q=AA-1001")
    assert foreign.status_code == 200
    assert foreign.get_json()["count"] == 0

    # ANVI must answer from the selected plant only.
    answer = client.post("/api/ask", json={"question": "Tell me about AA-1001"}).get_json()
    text = str(answer.get("answer", ""))
    assert "Alpha valve pressure" not in text
    assert "AA-1001" not in text or "not have" in text.lower() or "no" in text.lower()

    answer = client.post("/api/ask", json={"question": "Tell me about BB-2002"}).get_json()
    text = str(answer.get("answer", ""))
    assert "BB-2002" in text
    assert "Beta fan temperature" in text
