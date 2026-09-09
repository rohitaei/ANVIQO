import os
from pathlib import Path
import uuid


def build_app():
    db = Path(f"phase2_api_{uuid.uuid4().hex}.db")
    os.environ["ANVIQO_SECRET_KEY"] = "phase2-test-secret"
    os.environ["ANVIQO_ADMIN_USER"] = "phase2-admin"
    os.environ["ANVIQO_ADMIN_PASSWORD"] = "phase2-password"
    os.environ.pop("DATABASE_URL", None)
    os.environ["ANVIQO_TENANT_DB_URL"] = f"sqlite:///{db}"
    import importlib
    import anviqo_api_phase2
    importlib.reload(anviqo_api_phase2)
    return anviqo_api_phase2.app, db


def test_api_tenant_context_requires_login_and_bootstraps_membership():
    app, db = build_app()
    try:
        client = app.test_client()
        response = client.get("/api/tenant/context")
        assert response.status_code == 401

        login = client.post(
            "/login",
            data={"username": "phase2-admin", "password": "phase2-password"},
            follow_redirects=False,
        )
        assert login.status_code == 302

        context = client.get("/api/tenant/context")
        assert context.status_code == 200
        payload = context.get_json()
        assert payload["role"] == "ADMIN"
        assert payload["organization_id"]
        assert payload["plant_id"]
        assert "tenant:read" in payload["permissions"]
        assert "inventory:write" in payload["permissions"]

        audit = client.get("/api/tenant/audit?limit=10")
        assert audit.status_code == 200
        assert audit.get_json()["organization_id"] == payload["organization_id"]
    finally:
        db.unlink(missing_ok=True)


if __name__ == "__main__":
    test_api_tenant_context_requires_login_and_bootstraps_membership()
    print("PHASE2 API TENANT BOUNDARY: PASS")
