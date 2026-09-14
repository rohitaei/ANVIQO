"""ANVIQO Phase 2 tenant and authorization foundation.

This module is deliberately isolated from the frozen V5 intelligence modules.
It provides organization/plant/user/membership/role/permission storage,
tenant-scoped authorization, and a tenant-aware audit trail.

Production storage: PostgreSQL via DATABASE_URL.
Test storage: SQLite via ANVIQO_TENANT_DB_URL=sqlite:///... or sqlite:///:memory:.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TENANT_DB_URL = os.getenv("ANVIQO_TENANT_DB_URL", "").strip()

ROLE_PERMISSIONS = {
    "OWNER": {"tenant:read", "tenant:admin", "audit:read", "plant:read", "inventory:read", "inventory:write"},
    "ADMIN": {"tenant:read", "tenant:admin", "audit:read", "plant:read", "inventory:read", "inventory:write"},
    "ENGINEER": {"tenant:read", "audit:read", "plant:read", "inventory:read", "inventory:write"},
    "OPERATOR": {"tenant:read", "plant:read", "inventory:read"},
    "VIEWER": {"tenant:read", "plant:read", "inventory:read"},
}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def enabled() -> bool:
    return bool(TENANT_DB_URL or DATABASE_URL)


def _db_url() -> str:
    return TENANT_DB_URL or DATABASE_URL


def _is_sqlite() -> bool:
    return _db_url().startswith("sqlite:")


def _sqlite_path() -> str:
    url = _db_url()[len("sqlite:"):]
    if url == ":memory:" or url == "//:memory:":
        return ":memory:"
    if url.startswith("///"):
        return url[2:]
    if url.startswith("//"):
        return url[2:]
    return url


@contextmanager
def _connect() -> Iterator[Any]:
    url = _db_url()
    if url.startswith("sqlite:"):
        conn = sqlite3.connect(_sqlite_path())
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
        return

    if not url:
        raise RuntimeError("DATABASE_URL is required for tenant persistence")

    import psycopg
    conn = psycopg.connect(url)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _placeholder() -> str:
    return "?" if _is_sqlite() else "%s"


def init_schema() -> bool:
    if not enabled():
        return False

    if _is_sqlite():
        statements = [
            "CREATE TABLE IF NOT EXISTS anviqo_organizations (organization_id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS anviqo_plants (plant_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, slug TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TEXT NOT NULL, UNIQUE(organization_id, slug), FOREIGN KEY(organization_id) REFERENCES anviqo_organizations(organization_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_users (user_id TEXT PRIMARY KEY, external_username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS anviqo_roles (role_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_permissions (permission_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_role_permissions (role_id TEXT NOT NULL, permission_id TEXT NOT NULL, PRIMARY KEY(role_id, permission_id), FOREIGN KEY(role_id) REFERENCES anviqo_roles(role_id), FOREIGN KEY(permission_id) REFERENCES anviqo_permissions(permission_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_memberships (membership_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, organization_id TEXT NOT NULL, plant_id TEXT, role_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TEXT NOT NULL, UNIQUE(user_id, organization_id, plant_id), FOREIGN KEY(user_id) REFERENCES anviqo_users(user_id), FOREIGN KEY(organization_id) REFERENCES anviqo_organizations(organization_id), FOREIGN KEY(plant_id) REFERENCES anviqo_plants(plant_id), FOREIGN KEY(role_id) REFERENCES anviqo_roles(role_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_tenant_audit (audit_id TEXT PRIMARY KEY, actor_user_id TEXT, organization_id TEXT NOT NULL, plant_id TEXT, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL)",
        ]
    else:
        statements = [
            "CREATE TABLE IF NOT EXISTS anviqo_organizations (organization_id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS anviqo_plants (plant_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), name TEXT NOT NULL, slug TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(organization_id, slug))",
            "CREATE TABLE IF NOT EXISTS anviqo_users (user_id TEXT PRIMARY KEY, external_username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS anviqo_roles (role_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_permissions (permission_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_role_permissions (role_id TEXT NOT NULL REFERENCES anviqo_roles(role_id), permission_id TEXT NOT NULL REFERENCES anviqo_permissions(permission_id), PRIMARY KEY(role_id, permission_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_memberships (membership_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES anviqo_users(user_id), organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT REFERENCES anviqo_plants(plant_id), role_id TEXT NOT NULL REFERENCES anviqo_roles(role_id), status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(user_id, organization_id, plant_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_tenant_audit (audit_id TEXT PRIMARY KEY, actor_user_id TEXT, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT REFERENCES anviqo_plants(plant_id), action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
        ]

    with _connect() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
    return True


def seed_roles_permissions() -> None:
    init_schema()
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        for role, permissions in ROLE_PERMISSIONS.items():
            role_id = _id("role")
            role_insert = f"INSERT OR IGNORE INTO anviqo_roles(role_id,name,description) VALUES({p},{p},{p})" if _is_sqlite() else f"INSERT INTO anviqo_roles(role_id,name,description) VALUES({p},{p},{p}) ON CONFLICT(name) DO NOTHING"
            cur.execute(role_insert, (role_id, role, f"ANVIQO {role} role"))
            cur.execute(f"SELECT role_id FROM anviqo_roles WHERE name={p}", (role,))
            role_id = cur.fetchone()[0]
            for perm in permissions:
                perm_id = _id("perm")
                perm_insert = f"INSERT OR IGNORE INTO anviqo_permissions(permission_id,name,description) VALUES({p},{p},{p})" if _is_sqlite() else f"INSERT INTO anviqo_permissions(permission_id,name,description) VALUES({p},{p},{p}) ON CONFLICT(name) DO NOTHING"
                cur.execute(perm_insert, (perm_id, perm, perm))
                cur.execute(f"SELECT permission_id FROM anviqo_permissions WHERE name={p}", (perm,))
                perm_row = cur.fetchone()
                rp_insert = f"INSERT OR IGNORE INTO anviqo_role_permissions(role_id,permission_id) VALUES({p},{p})" if _is_sqlite() else f"INSERT INTO anviqo_role_permissions(role_id,permission_id) VALUES({p},{p}) ON CONFLICT DO NOTHING"
                cur.execute(rp_insert, (role_id, perm_row[0]))


def ensure_bootstrap(username: str, organization_name: str = "ANVIQO Customer", plant_name: str = "Primary Plant") -> dict[str, str] | None:
    if not enabled():
        return None
    init_schema()
    seed_roles_permissions()
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT organization_id FROM anviqo_organizations WHERE slug={p}", ("anviqo-customer",))
        row = cur.fetchone()
        org_id = row[0] if row else _id("org")
        if not row:
            if _is_sqlite():
                cur.execute(f"INSERT INTO anviqo_organizations(organization_id,name,slug,status,created_at) VALUES({p},{p},{p},{p},{p})", (org_id, organization_name, "anviqo-customer", "ACTIVE", _now()))
            else:
                cur.execute(f"INSERT INTO anviqo_organizations(organization_id,name,slug) VALUES({p},{p},{p})", (org_id, organization_name, "anviqo-customer"))
        cur.execute(f"SELECT plant_id FROM anviqo_plants WHERE organization_id={p} AND slug={p}", (org_id, "primary-plant"))
        row = cur.fetchone()
        plant_id = row[0] if row else _id("plant")
        if not row:
            if _is_sqlite():
                cur.execute(f"INSERT INTO anviqo_plants(plant_id,organization_id,name,slug,status,created_at) VALUES({p},{p},{p},{p},{p},{p})", (plant_id, org_id, plant_name, "primary-plant", "ACTIVE", _now()))
            else:
                cur.execute(f"INSERT INTO anviqo_plants(plant_id,organization_id,name,slug) VALUES({p},{p},{p},{p})", (plant_id, org_id, plant_name, "primary-plant"))
        cur.execute(f"SELECT user_id FROM anviqo_users WHERE external_username={p}", (str(username),))
        row = cur.fetchone()
        user_id = row[0] if row else _id("user")
        if not row:
            if _is_sqlite():
                cur.execute(f"INSERT INTO anviqo_users(user_id,external_username,display_name,status,created_at) VALUES({p},{p},{p},{p},{p})", (user_id, str(username), str(username), "ACTIVE", _now()))
            else:
                cur.execute(f"INSERT INTO anviqo_users(user_id,external_username,display_name) VALUES({p},{p},{p})", (user_id, str(username), str(username)))
        cur.execute(f"SELECT role_id FROM anviqo_roles WHERE name={p}", ("ADMIN",))
        role_id = cur.fetchone()[0]
        cur.execute(f"SELECT membership_id FROM anviqo_memberships WHERE user_id={p} AND organization_id={p} AND plant_id={p}", (user_id, org_id, plant_id))
        row = cur.fetchone()
        membership_id = row[0] if row else _id("membership")
        if not row:
            if _is_sqlite():
                cur.execute(f"INSERT INTO anviqo_memberships(membership_id,user_id,organization_id,plant_id,role_id,status,created_at) VALUES({p},{p},{p},{p},{p},{p},{p})", (membership_id, user_id, org_id, plant_id, role_id, "ACTIVE", _now()))
            else:
                cur.execute(f"INSERT INTO anviqo_memberships(membership_id,user_id,organization_id,plant_id,role_id) VALUES({p},{p},{p},{p},{p})", (membership_id, user_id, org_id, plant_id, role_id))
    return {"user_id": user_id, "organization_id": org_id, "plant_id": plant_id, "membership_id": membership_id, "role": "ADMIN"}


def create_organization(name: str, slug: str) -> str:
    init_schema(); org_id = _id("org"); p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        if _is_sqlite():
            cur.execute(f"INSERT INTO anviqo_organizations VALUES({p},{p},{p},'ACTIVE',{p})", (org_id,name,slug,_now()))
        else:
            cur.execute(f"INSERT INTO anviqo_organizations(organization_id,name,slug) VALUES({p},{p},{p})", (org_id,name,slug))
    return org_id


def create_plant(organization_id: str, name: str, slug: str) -> str:
    init_schema(); plant_id = _id("plant"); p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        if _is_sqlite():
            cur.execute(f"INSERT INTO anviqo_plants VALUES({p},{p},{p},{p},'ACTIVE',{p})", (plant_id,organization_id,name,slug,_now()))
        else:
            cur.execute(f"INSERT INTO anviqo_plants(plant_id,organization_id,name,slug) VALUES({p},{p},{p},{p})", (plant_id,organization_id,name,slug))
    return plant_id


def create_user(username: str, display_name: str = "") -> str:
    init_schema(); user_id = _id("user"); p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        if _is_sqlite():
            cur.execute(f"INSERT INTO anviqo_users VALUES({p},{p},{p},'ACTIVE',{p})", (user_id,username,display_name or username,_now()))
        else:
            cur.execute(f"INSERT INTO anviqo_users(user_id,external_username,display_name) VALUES({p},{p},{p})", (user_id,username,display_name or username))
    return user_id


def create_membership(user_id: str, organization_id: str, plant_id: str, role: str) -> str:
    init_schema(); seed_roles_permissions(); membership_id = _id("membership"); p = _placeholder(); role = role.upper()
    if role not in ROLE_PERMISSIONS: raise ValueError(f"Unknown role: {role}")
    with _connect() as conn:
        cur = conn.cursor(); cur.execute(f"SELECT role_id FROM anviqo_roles WHERE name={p}", (role,)); role_id = cur.fetchone()[0]
        if _is_sqlite():
            cur.execute(f"INSERT INTO anviqo_memberships VALUES({p},{p},{p},{p},{p},'ACTIVE',{p})", (membership_id,user_id,organization_id,plant_id,role_id,_now()))
        else:
            cur.execute(f"INSERT INTO anviqo_memberships(membership_id,user_id,organization_id,plant_id,role_id) VALUES({p},{p},{p},{p},{p})", (membership_id,user_id,organization_id,plant_id,role_id))
    return membership_id


def get_membership(user_id: str, organization_id: str, plant_id: str | None = None) -> dict[str, Any] | None:
    if not enabled(): return None
    init_schema(); p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        if plant_id is None:
            cur.execute(f"SELECT m.membership_id,m.user_id,m.organization_id,m.plant_id,r.name,m.status FROM anviqo_memberships m JOIN anviqo_roles r ON r.role_id=m.role_id WHERE m.user_id={p} AND m.organization_id={p} AND m.plant_id IS NULL AND m.status='ACTIVE'", (user_id,organization_id))
        else:
            cur.execute(f"SELECT m.membership_id,m.user_id,m.organization_id,m.plant_id,r.name,m.status FROM anviqo_memberships m JOIN anviqo_roles r ON r.role_id=m.role_id WHERE m.user_id={p} AND m.organization_id={p} AND m.plant_id={p} AND m.status='ACTIVE'", (user_id,organization_id,plant_id))
        row = cur.fetchone()
    if not row: return None
    return {"membership_id":row[0],"user_id":row[1],"organization_id":row[2],"plant_id":row[3],"role":row[4],"status":row[5]}


def authorize(actor: dict[str, Any], permission: str, organization_id: str, plant_id: str | None = None) -> bool:
    if not actor or not actor.get("user_id"): return False
    if actor.get("organization_id") != organization_id: return False
    if plant_id is not None and actor.get("plant_id") != plant_id: return False
    membership = get_membership(actor["user_id"], organization_id, plant_id)
    if not membership: return False
    return permission in ROLE_PERMISSIONS.get(membership["role"], set())


def record_audit(actor: dict[str, Any], action: str, resource_type: str, resource_id: str = "", metadata: dict[str, Any] | None = None) -> str:
    if not enabled(): raise RuntimeError("Tenant persistence is disabled")
    org_id = str(actor.get("organization_id", "")); plant_id = actor.get("plant_id"); user_id = actor.get("user_id")
    if not org_id: raise ValueError("Audit actor must contain organization_id")
    audit_id = _id("audit"); p = _placeholder(); meta = json.dumps(metadata or {}, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.cursor()
        if _is_sqlite():
            cur.execute(f"INSERT INTO anviqo_tenant_audit VALUES({p},{p},{p},{p},{p},{p},{p},{p},{p})", (audit_id,user_id,org_id,plant_id,action,resource_type,resource_id,meta,_now()))
        else:
            cur.execute(f"INSERT INTO anviqo_tenant_audit(audit_id,actor_user_id,organization_id,plant_id,action,resource_type,resource_id,metadata) VALUES({p},{p},{p},{p},{p},{p},{p},{p}::jsonb)", (audit_id,user_id,org_id,plant_id,action,resource_type,resource_id,meta))
    return audit_id


def list_audit(actor: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
    if not authorize(actor, "audit:read", actor.get("organization_id", ""), actor.get("plant_id")):
        raise PermissionError("Audit access denied for tenant context")
    p = _placeholder(); org_id = actor["organization_id"]; plant_id = actor.get("plant_id")
    with _connect() as conn:
        cur = conn.cursor()
        if plant_id:
            cur.execute(f"SELECT audit_id,actor_user_id,organization_id,plant_id,action,resource_type,resource_id,metadata,created_at FROM anviqo_tenant_audit WHERE organization_id={p} AND plant_id={p} ORDER BY created_at DESC LIMIT {int(limit)}", (org_id,plant_id))
        else:
            cur.execute(f"SELECT audit_id,actor_user_id,organization_id,plant_id,action,resource_type,resource_id,metadata,created_at FROM anviqo_tenant_audit WHERE organization_id={p} ORDER BY created_at DESC LIMIT {int(limit)}", (org_id,))
        rows = cur.fetchall()
    result=[]
    for row in rows:
        meta=row[7]
        if isinstance(meta,str):
            try: meta=json.loads(meta)
            except Exception: meta={}
        result.append({"audit_id":row[0],"actor_user_id":row[1],"organization_id":row[2],"plant_id":row[3],"action":row[4],"resource_type":row[5],"resource_id":row[6],"metadata":meta,"created_at":row[8]})
    return result
