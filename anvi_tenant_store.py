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

# Render PostgreSQL requires TLS. Normalize the production connection once at
# process startup so every tenant-store connection uses the same secure path.
if not TENANT_DB_URL.startswith("sqlite:") and (TENANT_DB_URL or DATABASE_URL):
    if TENANT_DB_URL and "sslmode=" not in TENANT_DB_URL.lower():
        TENANT_DB_URL += ("&" if "?" in TENANT_DB_URL else "?") + "sslmode=require"
    elif not TENANT_DB_URL and "sslmode=" not in DATABASE_URL.lower():
        DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

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
        with _connect() as conn:
            cur = conn.cursor()
            for sql in statements:
                cur.execute(sql)
        return True

    with _connect() as conn:
        cur = conn.cursor()
        statements = [
            "CREATE TABLE IF NOT EXISTS anviqo_organizations (organization_id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS anviqo_plants (plant_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, slug TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(organization_id, slug))",
            "CREATE TABLE IF NOT EXISTS anviqo_users (user_id TEXT PRIMARY KEY, external_username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS anviqo_roles (role_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_permissions (permission_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '')",
            "CREATE TABLE IF NOT EXISTS anviqo_role_permissions (role_id TEXT NOT NULL, permission_id TEXT NOT NULL, PRIMARY KEY(role_id, permission_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_memberships (membership_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, organization_id TEXT NOT NULL, plant_id TEXT, role_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(user_id, organization_id, plant_id))",
            "CREATE TABLE IF NOT EXISTS anviqo_tenant_audit (audit_id TEXT PRIMARY KEY, actor_user_id TEXT, organization_id TEXT NOT NULL, plant_id TEXT, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
        ]
        for sql in statements:
            cur.execute(sql)
    return True
