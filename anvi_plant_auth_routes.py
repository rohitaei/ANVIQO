"""ANVIQO plant login and plant-user provisioning routes.

Authentication/context only; frozen V5 intelligence and PLC/SCADA boundaries
remain unchanged. Provisioning is organization-scoped and least-privilege.
"""
from __future__ import annotations

import os
from pathlib import Path
from flask import jsonify, request, session, Response, redirect

from phase6_enterprise_runtime import app
import anvi_tenant_store as store
import anvi_plant_auth as plant_auth

_BASE = Path(__file__).resolve().parent
_LOGIN_PAGE = _BASE / "plant_login.html"
_ADMIN_PAGE = _BASE / "plant_user_admin.html"


def _html_page(path: Path):
    if not path.is_file():
        return Response(f"ANVIQO page unavailable: {path.name}", status=500, mimetype="text/plain")
    response = Response(path.read_text(encoding="utf-8"), status=200, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def _actor() -> dict:
    return {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}


def _admin() -> bool:
    actor = _actor()
    return bool(actor["user_id"] and actor["organization_id"] and actor["role"] in {"OWNER", "ADMIN"})


def _owner() -> bool:
    return _actor()["role"] == "OWNER"


def _plant_belongs_to_actor_org(plant_id: str) -> bool:
    actor = _actor()
    if not plant_id or not actor["organization_id"]: return False
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1", (plant_id, actor["organization_id"]))
        return cur.fetchone() is not None


def _user_in_actor_org(username: str) -> bool:
    actor = _actor(); p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM anviqo_users u JOIN anviqo_memberships m ON m.user_id=u.user_id WHERE u.external_username={p} AND m.organization_id={p} AND m.status='ACTIVE' LIMIT 1", (username, actor["organization_id"]))
        return cur.fetchone() is not None


@app.before_request
def plant_login_interceptor():
    if request.path != "/login": return None
    plant_auth.init_auth_schema()
    if request.method == "GET": return _html_page(_LOGIN_PAGE)
    username = request.form.get("username", "").strip(); password = request.form.get("password", ""); plant_slug = request.form.get("plant_slug", "").strip().lower()
    admin_user = os.environ.get("ANVIQO_ADMIN_USER", ""); admin_password = os.environ.get("ANVIQO_ADMIN_PASSWORD", "")
    if username == admin_user and password == admin_password:
        context = store.ensure_bootstrap(username); session.clear(); session.update({"authenticated": True, "username": username, "role": "ADMIN", **(context or {})}); return redirect("/enterprise")
    identity = plant_auth.authenticate(username, password, plant_slug)
    if not identity: return _html_page(_LOGIN_PAGE)
    session.clear(); session.update({"authenticated": True, **identity})
    try: store.record_audit(identity, "LOGIN", "PLANT", identity["plant_id"], {"auth_version": plant_auth.AUTH_VERSION})
    except Exception: pass
    return redirect("/enterprise")


@app.get("/api/session/context")
def session_context():
    if not session.get("authenticated"): return jsonify({"status": "UNAUTHORIZED"}), 401
    return jsonify({"status": "OK", "username": session.get("username", ""), "role": session.get("role", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "plant_name": session.get("plant_name", ""), "plant_slug": session.get("plant_slug", "")})


def _serve_admin_page():
    if not _admin(): return redirect("/login")
    return _html_page(_ADMIN_PAGE)


@app.get("/admin/users")
@app.get("/admin/plant-users")
@app.get("/account/create")
def admin_users_page():
    return _serve_admin_page()


@app.get("/api/admin/plants")
def admin_plants():
    if not _admin(): return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    actor = _actor(); p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute(f"SELECT plant_id,name,slug,status FROM anviqo_plants WHERE organization_id={p} ORDER BY name", (actor["organization_id"],)); rows = cur.fetchall()
    return jsonify({"status": "OK", "plants": [{"plant_id": r[0], "name": r[1], "slug": r[2], "status": r[3]} for r in rows]})


@app.post("/api/admin/plants")
def admin_create_plant():
    if not _admin(): return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    slug = str(body.get("slug", "")).strip().lower()
    if not name or not slug:
        return jsonify({"status": "INVALID", "message": "Plant name and plant slug are required"}), 400
    try:
        plant_id = store.create_plant(_actor()["organization_id"], name, slug)
        try: store.record_audit(_actor(), "CREATE_PLANT", "PLANT", plant_id, {"name": name, "slug": slug})
        except Exception: pass
        return jsonify({"status": "OK", "plant_id": plant_id, "name": name, "slug": slug}), 201
    except Exception as exc:
        return jsonify({"status": "ERROR", "message": str(exc)}), 400


@app.post("/api/admin/plant-users")
def create_plant_user():
    if not _admin(): return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    body = request.get_json(silent=True) or {}; username = str(body.get("username", "")).strip(); display_name = str(body.get("display_name", username)).strip(); password = str(body.get("password", "")); plant_id = str(body.get("plant_id", "")).strip(); role = str(body.get("role", "OPERATOR")).upper().strip()
    if not username or not password or not plant_id: return jsonify({"status": "INVALID", "message": "username, password and plant_id are required"}), 400
    if len(password) < 8: return jsonify({"status": "INVALID", "message": "Password must contain at least 8 characters"}), 400
    if role not in store.ROLE_PERMISSIONS: return jsonify({"status": "INVALID", "message": "Unsupported role"}), 400
    if role in {"OWNER", "ADMIN"} and not _owner(): return jsonify({"status": "FORBIDDEN", "message": "Only OWNER may provision ADMIN/OWNER accounts"}), 403
    if not _plant_belongs_to_actor_org(plant_id): return jsonify({"status": "FORBIDDEN", "message": "Plant is not active in your organization"}), 403
    if _user_in_actor_org(username): return jsonify({"status": "CONFLICT", "message": "User already has an active membership in this organization"}), 409
    try:
        user_id = store.create_user(username, display_name); store.create_membership(user_id, _actor()["organization_id"], plant_id, role); plant_auth.set_password(username, password)
        try: store.record_audit(_actor(), "CREATE_USER", "USER", user_id, {"plant_id": plant_id, "role": role})
        except Exception: pass
        return jsonify({"status": "OK", "user_id": user_id, "username": username, "plant_id": plant_id, "role": role, "password_stored_as": "scrypt_hash"}), 201
    except Exception as exc: return jsonify({"status": "ERROR", "message": str(exc)}), 400


@app.post("/api/admin/plant-user-password")
def change_plant_user_password():
    if not _admin(): return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    body = request.get_json(silent=True) or {}; username = str(body.get("username", "")).strip(); password = str(body.get("password", ""))
    if not username or not password: return jsonify({"status": "INVALID", "message": "username and password are required"}), 400
    if len(password) < 8: return jsonify({"status": "INVALID", "message": "Password must contain at least 8 characters"}), 400
    if not _user_in_actor_org(username): return jsonify({"status": "FORBIDDEN", "message": "User is not active in your organization"}), 403
    try:
        plant_auth.set_password(username, password)
        try: store.record_audit(_actor(), "CHANGE_PASSWORD", "USER", username, {})
        except Exception: pass
        return jsonify({"status": "OK", "username": username})
    except Exception as exc: return jsonify({"status": "ERROR", "message": str(exc)}), 400


@app.get("/api/my-plants")
def my_plants():
    if not session.get("authenticated"): return jsonify({"status": "UNAUTHORIZED"}), 401
    return jsonify({"status": "OK", "plants": plant_auth.list_user_plants(session.get("username", ""))})


__all__ = ["plant_login_interceptor", "session_context", "admin_users_page", "admin_plants", "admin_create_plant", "create_plant_user", "change_plant_user_password", "my_plants"]
