import os
import uuid
from pathlib import Path


def load_store():
    db = Path(f"phase2_tenant_{uuid.uuid4().hex}.db")
    os.environ["ANVIQO_TENANT_DB_URL"] = f"sqlite:///{db}"
    import importlib
    import anviqo_tenant_store
    return importlib.reload(anviqo_tenant_store), db


def test_organization_plant_user_membership_role_permission_chain():
    store, db = load_store()
    try:
        store.init_schema()
        store.seed_roles_permissions()
        org = store.create_organization("Plant A Org", "plant-a-org")
        plant = store.create_plant(org, "Plant A", "plant-a")
        user = store.create_user("alice", "Alice")
        store.create_membership(user, org, plant, "ADMIN")

        membership = store.get_membership(user, org, plant)
        assert membership is not None
        assert membership["role"] == "ADMIN"
        assert "inventory:write" in store.ROLE_PERMISSIONS["ADMIN"]
        assert "inventory:write" not in store.ROLE_PERMISSIONS["VIEWER"]
    finally:
        db.unlink(missing_ok=True)


def test_tenant_isolation_and_authorization():
    store, db = load_store()
    try:
        store.init_schema()
        store.seed_roles_permissions()
        org_a = store.create_organization("Org A", "org-a")
        org_b = store.create_organization("Org B", "org-b")
        plant_a = store.create_plant(org_a, "Plant A", "plant-a")
        plant_b = store.create_plant(org_b, "Plant B", "plant-b")
        user_a = store.create_user("alice", "Alice")
        user_b = store.create_user("bob", "Bob")
        store.create_membership(user_a, org_a, plant_a, "ADMIN")
        store.create_membership(user_b, org_b, plant_b, "ADMIN")

        actor_a = {"user_id": user_a, "organization_id": org_a, "plant_id": plant_a}
        actor_b = {"user_id": user_b, "organization_id": org_b, "plant_id": plant_b}

        assert store.authorize(actor_a, "tenant:read", org_a, plant_a)
        assert store.authorize(actor_b, "tenant:read", org_b, plant_b)
        assert not store.authorize(actor_a, "tenant:read", org_b, plant_b)
        assert not store.authorize(actor_b, "inventory:write", org_a, plant_a)

        store.record_audit(actor_a, "READ", "equipment", "PT-303")
        store.record_audit(actor_b, "READ", "equipment", "TT-201")
        audit_a = store.list_audit(actor_a)
        audit_b = store.list_audit(actor_b)

        assert len(audit_a) == 1
        assert audit_a[0]["organization_id"] == org_a
        assert audit_a[0]["plant_id"] == plant_a
        assert audit_a[0]["resource_id"] == "PT-303"
        assert len(audit_b) == 1
        assert audit_b[0]["organization_id"] == org_b
        assert audit_b[0]["plant_id"] == plant_b
        assert audit_b[0]["resource_id"] == "TT-201"
        assert not any(row["organization_id"] == org_b for row in audit_a)
        assert not any(row["organization_id"] == org_a for row in audit_b)
    finally:
        db.unlink(missing_ok=True)


def test_unknown_or_cross_tenant_membership_denies_access():
    store, db = load_store()
    try:
        store.init_schema()
        store.seed_roles_permissions()
        org_a = store.create_organization("Org A", "org-a")
        org_b = store.create_organization("Org B", "org-b")
        plant_a = store.create_plant(org_a, "Plant A", "plant-a")
        plant_b = store.create_plant(org_b, "Plant B", "plant-b")
        user_a = store.create_user("alice", "Alice")
        store.create_membership(user_a, org_a, plant_a, "VIEWER")
        actor_a = {"user_id": user_a, "organization_id": org_a, "plant_id": plant_a}

        assert not store.authorize(actor_a, "tenant:admin", org_a, plant_a)
        assert not store.authorize(actor_a, "audit:read", org_b, plant_b)
        assert not store.authorize(actor_a, "inventory:write", org_a, plant_a)
    finally:
        db.unlink(missing_ok=True)


if __name__ == "__main__":
    test_organization_plant_user_membership_role_permission_chain()
    test_tenant_isolation_and_authorization()
    test_unknown_or_cross_tenant_membership_denies_access()
    print("PHASE2 TENANT FOUNDATION: PASS")
