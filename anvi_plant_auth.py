"""ANVIQO plant-scoped authentication layer.

Uses the existing Phase 2 tenant store. Credentials are stored as salted
scrypt hashes in the same tenant database; plaintext passwords are never
stored. This layer does not modify V5 intelligence or PLC/SCADA behavior.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Any

import anvi_tenant_store as store

AUTH_VERSION = "ANVIQO-PLANT-AUTH-V1"


def _placeholder() -> str:
    return "?" if store._is_sqlite() else "%s"


def _debug(message: str) -> None:
    if os.getenv("ANVIQO_AUTH_DEBUG", "").strip() == "1":
        print(f"ANVIQO_AUTH_DEBUG {message}", flush=True)


def init_auth_schema() -> bool:
    """Ensure password columns exist without aborting PostgreSQL transactions."""
    if not store.enabled():
        _debug("storage=DISABLED")
        return False
    store.init_schema()
    with store._connect() as conn:
        cur = conn.cursor()
        if store._is_sqlite():
            cur.execute("PRAGMA table_info(anviqo_users)")
            columns = {row[1] for row in cur.fetchall()}
            if "password_hash" not in columns:
                cur.execute("ALTER TABLE anviqo_users ADD COLUMN password_hash TEXT")
            if "password_salt" not in columns:
                cur.execute("ALTER TABLE anviqo_users ADD COLUMN password_salt TEXT")
        else:
            cur.execute("ALTER TABLE anviqo_users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            cur.execute("ALTER TABLE anviqo_users ADD COLUMN IF NOT EXISTS password_salt TEXT")
    return True


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if not password or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return digest.hex(), salt.hex()


def set_password(username: str, password: str) -> None:
    init_auth_schema()
    password_hash, password_salt = _hash_password(password)
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE anviqo_users SET password_hash={p}, password_salt={p} WHERE LOWER(external_username)=LOWER({p})",
            (password_hash, password_salt, username.strip()),
        )
        if cur.rowcount != 1:
            raise ValueError("User not found")


def _verify(password: str, password_hash: str, password_salt: str) -> bool:
    try:
        salt = bytes.fromhex(password_salt)
        expected = bytes.fromhex(password_hash)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def authenticate(username: str, password: str, plant_slug: str) -> dict[str, Any] | None:
    """Authenticate a user and require an ACTIVE membership for a plant ID, name, or slug."""
    username = str(username or "").strip()
    plant_slug = str(plant_slug or "").strip()
    if not username or not password or not plant_slug:
        _debug(f"input_missing username={bool(username)} password={bool(password)} plant={bool(plant_slug)}")
        return None
    init_auth_schema()
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT user_id,display_name,status,password_hash,password_salt FROM anviqo_users WHERE LOWER(external_username)=LOWER({p})",
            (username,),
        )
        user = cur.fetchone()
        if not user:
            _debug("user_found=False")
            return None
        if user[2] != "ACTIVE":
            _debug(f"user_found=True user_status={user[2]}")
            return None
        if not user[3] or not user[4]:
            _debug("user_found=True password_material=False")
            return None
        password_ok = _verify(password, user[3], user[4])
        _debug(f"user_found=True user_status=ACTIVE password_material=True password_ok={password_ok}")
        if not password_ok:
            return None
        cur.execute(
            f"""SELECT m.organization_id,m.plant_id,r.name,o.name,p.name,p.slug
                FROM anviqo_memberships m
                JOIN anviqo_roles r ON r.role_id=m.role_id
                JOIN anviqo_organizations o ON o.organization_id=m.organization_id
                JOIN anviqo_plants p ON p.plant_id=m.plant_id
                WHERE m.user_id={p}
                  AND (LOWER(p.slug)=LOWER({p}) OR LOWER(p.name)=LOWER({p}) OR p.plant_id={p})
                  AND m.status='ACTIVE' AND p.status='ACTIVE'""",
            (user[0], plant_slug, plant_slug, plant_slug),
        )
        membership = cur.fetchone()
        _debug(f"membership_found={bool(membership)}")
    if not membership:
        return None
    return {
        "user_id": user[0],
        "username": username,
        "display_name": user[1],
        "organization_id": membership[0],
        "plant_id": membership[1],
        "role": membership[2],
        "organization_name": membership[3],
        "plant_name": membership[4],
        "plant_slug": membership[5],
        "auth_version": AUTH_VERSION,
    }


def list_user_plants(username: str) -> list[dict[str, Any]]:
    """Return only active plants to which the user has an active membership."""
    if not store.enabled():
        return []
    init_auth_schema()
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""SELECT m.organization_id,m.plant_id,o.name,p.name,p.slug,r.name
                FROM anviqo_users u
                JOIN anviqo_memberships m ON m.user_id=u.user_id
                JOIN anviqo_organizations o ON o.organization_id=m.organization_id
                JOIN anviqo_plants p ON p.plant_id=m.plant_id
                JOIN anviqo_roles r ON r.role_id=m.role_id
                WHERE LOWER(u.external_username)=LOWER({p}) AND m.status='ACTIVE' AND p.status='ACTIVE'
                ORDER BY p.name""",
            (username,),
        )
        rows = cur.fetchall()
    return [
        {"organization_id": r[0], "plant_id": r[1], "organization_name": r[2], "plant_name": r[3], "plant_slug": r[4], "role": r[5]}
        for r in rows
    ]


__all__ = ["AUTH_VERSION", "init_auth_schema", "set_password", "authenticate", "list_user_plants"]