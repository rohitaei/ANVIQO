import os
import subprocess
import sys
import uuid
from pathlib import Path


def test_api_tenant_context_requires_login_and_bootstraps_membership():
    db = Path(f"phase2_api_{uuid.uuid4().hex}.db")
    script = r'''
from anviqo_api_phase2 import app
client = app.test_client()
response = client.get("/api/tenant/context")
assert response.status_code == 401
login = client.post("/login", data={"username": "phase2-admin", "password": "phase2-password"}, follow_redirects=False)
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
print("PHASE2 API TENANT BOUNDARY: PASS")
'''
    env = os.environ.copy()
    env.update({
        "ANVIQO_SECRET_KEY": "phase2-test-secret",
        "ANVIQO_ADMIN_USER": "phase2-admin",
        "ANVIQO_ADMIN_PASSWORD": "phase2-password",
        "ANVIQO_TENANT_DB_URL": f"sqlite://{db}",
    })
    env.pop("DATABASE_URL", None)
    try:
        result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
        assert "PHASE2 API TENANT BOUNDARY: PASS" in result.stdout
    finally:
        db.unlink(missing_ok=True)


if __name__ == "__main__":
    test_api_tenant_context_requires_login_and_bootstraps_membership()
    print("PHASE2 API TENANT BOUNDARY: PASS")
