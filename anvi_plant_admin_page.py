"""Reliable plant-user management page route.

Keeps provisioning UI separate from frozen V5 intelligence and PLC/SCADA.
"""
from __future__ import annotations

from pathlib import Path
from flask import redirect, session, send_file, url_for

from phase6_enterprise_runtime import app
import anvi_plant_auth_routes as auth_routes

_PAGE = Path(__file__).resolve().with_name("plant_user_admin.html")


def _admin() -> bool:
    actor = auth_routes._actor()
    return bool(actor["user_id"] and actor["organization_id"] and actor["role"] in {"OWNER", "ADMIN"})


def _serve():
    if not _admin():
        return redirect(url_for("plant_login_interceptor"))
    return send_file(_PAGE)

@app.get("/admin/users")
def plant_user_admin_page_v2():
    return _serve()

@app.get("/admin/plant-users")
def plant_user_admin_page_alias():
    return _serve()

@app.get("/account/create")
def plant_user_admin_create_alias():
    return _serve()

__all__ = ["plant_user_admin_page_v2", "plant_user_admin_page_alias", "plant_user_admin_create_alias"]
