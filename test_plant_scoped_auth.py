import os
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
