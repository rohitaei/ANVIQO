"""Bridge plant authentication/provisioning onto the actual Render app."""
from __future__ import annotations

import os
from pathlib import Path
from flask import redirect, Response

from anviqo_spare_query_guard import app
import anvi_plant_auth_routes as auth
import anvi_tenant_store as tenant_store

_PAGE = Path(__file__).resolve().with_name("plant_user_admin.html")

# Safe production diagnostic: never logs DATABASE_URL itself.
print(
    "ANVIQO_AUTH_STORAGE",
    {
        "database_url_configured": bool(os.getenv("DATABASE_URL", "").strip()),
        "tenant_db_url_configured": bool(os.getenv("ANVIQO_TENANT_DB_URL", "").strip()),
        "tenant_store_enabled": tenant_store.enabled(),
    },
    flush=True,
)

# Reuse the hardened authentication logic on the actual production Flask app.
# Direct list registration keeps imports safe even when this bridge is loaded after
# the Flask application has already served a request.
from werkzeug.routing import Rule

if auth.plant_login_interceptor not in app.before_request_funcs.setdefault(None, []):
    app.before_request_funcs[None].append(auth.plant_login_interceptor)

def deployed_session_context():
    return auth.session_context()

def deployed_admin_users_page():
    if not auth._admin():
        return redirect("/login")
    if not _PAGE.is_file():
        return Response("ANVIQO Plant User Management page unavailable.", status=500, mimetype="text/plain")
    html = _PAGE.read_text(encoding="utf-8")
    response = Response(html, status=200, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

def deployed_admin_plants():
    return auth.admin_plants()

def deployed_create_plant_user():
    return auth.create_plant_user()

def deployed_change_plant_user_password():
    return auth.change_plant_user_password()

def deployed_my_plants():
    return auth.my_plants()

def add_plant_user_management_nav(response):
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "text/html" not in content_type:
        return response
    try:
        html = response.get_data(as_text=True)
        marker = '<div class="nav-title">SYSTEM</div>'
        link = '<a id="plantUserManagementNav" href="/account/create" style="display:block;padding:10px 14px;color:inherit;text-decoration:none;cursor:pointer;">🏭 Plant &amp; User Management</a>'
        if marker in html and 'id="plantUserManagementNav"' not in html:
            html = html.replace(marker, marker + "\n" + link, 1)
            response.set_data(html)
    except Exception:
        pass
    return response

if add_plant_user_management_nav not in app.after_request_funcs.setdefault(None, []):
    app.after_request_funcs[None].append(add_plant_user_management_nav)

_routes = [
    ("deployed_session_context", "/api/session/context", ["GET"], deployed_session_context),
    ("deployed_admin_users_page", "/admin/users", ["GET"], deployed_admin_users_page),
    ("deployed_admin_users_page_plant_users", "/admin/plant-users", ["GET"], deployed_admin_users_page),
    ("deployed_admin_users_page_create", "/account/create", ["GET"], deployed_admin_users_page),
    ("deployed_admin_plants", "/api/admin/plants", ["GET"], deployed_admin_plants),
    ("deployed_create_plant_user", "/api/admin/plant-users", ["POST"], deployed_create_plant_user),
    ("deployed_change_plant_user_password", "/api/admin/plant-user-password", ["POST"], deployed_change_plant_user_password),
    ("deployed_my_plants", "/api/my-plants", ["GET"], deployed_my_plants),
]
for _endpoint, _path, _methods, _view in _routes:
    if _endpoint not in app.view_functions:
        app.view_functions[_endpoint] = _view
    if not any(r.endpoint == _endpoint and r.rule == _path for r in app.url_map.iter_rules()):
        app.url_map.add(Rule(_path, methods=_methods, endpoint=_endpoint))


__all__ = [
    "deployed_session_context",
    "deployed_admin_users_page",
    "deployed_admin_plants",
    "deployed_create_plant_user",
    "deployed_change_plant_user_password",
    "deployed_my_plants",
    "add_plant_user_management_nav",
]

