"""ANVIQO plant login and plant-user provisioning routes.

Attaches to the existing enterprise Flask app. It is authentication/context
only; frozen V5 intelligence and PLC/SCADA boundaries are unchanged.
"""
from __future__ import annotations

import os
from flask import jsonify, request, session, send_from_directory, redirect, url_for

from phase6_enterprise_runtime import app
import anvi_tenant_store as store
import anvi_plant_auth as plant_auth


def _actor() -> dict:
    return {
        "user_id": session.get("user_id", ""),
        "organization_id": session.get("organization_id", ""),
        "plant_id": session.get("plant_id", ""),
        "role": session.get("role", ""),
        "username": session.get("username", ""),
    }


def _admin() -> bool:
    actor = _actor()
    if not actor["user_id"] or not actor["organization_id"]:
        return False
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM anviqo_memberships m JOIN anviqo_roles r ON r.role_id=m.role_id WHERE m.user_id={p} AND m.organization_id={p} AND m.status='ACTIVE' AND r.name IN ('OWNER','ADMIN') LIMIT 1",
            (actor["user_id"], actor["organization_id"]),
        )
        return cur.fetchone() is not None


@app.before_request
def plant_login_interceptor():
    if request.path != "/login":
        return None
    plant_auth.init_auth_schema()
    if request.method == "GET":
        return send_from_directory(".", "plant_login.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    plant_slug = request.form.get("plant_slug", "").strip().lower()

    # Preserve the existing environment-admin login while binding it to the
    # bootstrapped tenant/primary plant context.
    admin_user = os.environ.get("ANVIQO_ADMIN_USER", "")
    admin_password = os.environ.get("ANVIQO_ADMIN_PASSWORD", "")
    if username == admin_user and password == admin_password:
        context = store.ensure_bootstrap(username)
        session.clear()
        session.update({"authenticated": True, "username": username, "role": "ADMIN", **(context or {})})
        return redirect(url_for("dashboard"))

    identity = plant_auth.authenticate(username, password, plant_slug)
    if not identity:
        return send_from_directory(".", "plant_login.html")
    session.clear()
    session.update({"authenticated": True, **identity})
    try:
        store.record_audit(identity, "LOGIN", "PLANT", identity["plant_id"], {"auth_version": plant_auth.AUTH_VERSION})
    except Exception:
        pass
    return redirect(url_for("dashboard"))


@app.get("/api/session/context")
def session_context():
    if not session.get("authenticated"):
        return jsonify({"status": "UNAUTHORIZED"}), 401
    return jsonify({
        "status": "OK",
        "username": session.get("username", ""),
        "role": session.get("role", ""),
        "organization_id": session.get("organization_id", ""),
        "plant_id": session.get("plant_id", ""),
        "plant_name": session.get("plant_name", ""),
        "plant_slug": session.get("plant_slug", ""),
    })


@app.post("/api/admin/plant-users")
def create_plant_user():
    if not _admin():
        return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    display_name = str(body.get("display_name", username)).strip()
    password = str(body.get("password", ""))
    plant_id = str(body.get("plant_id", "")).strip()
    role = str(body.get("role", "OPERATOR")).upper().strip()
    if not username or not password or not plant_id:
        return jsonify({"status": "INVALID", "message": "username, password and plant_id are required"}), 400
    if role not in store.ROLE_PERMISSIONS:
        return jsonify({"status": "INVALID", "message": "Unsupported role"}), 400
    try:
        user_id = store.create_user(username, display_name)
        store.create_membership(user_id, _actor()["organization_id"], plant_id, role)
        plant_auth.set_password(username, password)
        return jsonify({"status": "OK", "user_id": user_id, "username": username, "plant_id": plant_id, "role": role, "password_stored_as": "scrypt_hash"}), 201
    except Exception as exc:
        return jsonify({"status": "ERROR", "message": str(exc)}), 400


@app.post("/api/admin/plant-user-password")
def change_plant_user_password():
    if not _admin():
        return jsonify({"status": "FORBIDDEN", "message": "Organization ADMIN/OWNER access required"}), 403
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not username or not password:
        return jsonify({"status": "INVALID", "message": "username and password are required"}), 400
    try:
        plant_auth.set_password(username, password)
        return jsonify({"status": "OK", "username": username})
    except Exception as exc:
        return jsonify({"status": "ERROR", "message": str(exc)}), 400


@app.get("/api/my-plants")
def my_plants():
    if not session.get("authenticated"):
        return jsonify({"status": "UNAUTHORIZED"}), 401
    return jsonify({"status": "OK", "plants": plant_auth.list_user_plants(session.get("username", ""))})


__all__ = ["plant_login_interceptor", "session_context", "create_plant_user", "change_plant_user_password", "my_plants"]
