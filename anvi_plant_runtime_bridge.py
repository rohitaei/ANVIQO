"""Bridge plant authentication/provisioning onto the actual Render app.

Render currently starts failure_prediction_dashboard_runtime, whose Flask app
comes from anviqo_spare_query_guard. The enterprise auth module historically
registered on the Phase 6 app instead, leaving these routes absent in the
actual deployed process. This bridge registers the same hardened handlers on
the deployed app without changing V5 intelligence or PLC/SCADA controls.
"""
from __future__ import annotations

from flask import redirect, request, send_from_directory, url_for

from anviqo_spare_query_guard import app
import anvi_plant_auth_routes as auth


# Reuse the hardened authentication logic; register it on the actual runtime app.
app.before_request(auth.plant_login_interceptor)


@app.get("/api/session/context")
def deployed_session_context():
    return auth.session_context()


@app.get("/admin/users")
@app.get("/admin/plant-users")
@app.get("/account/create")
def deployed_admin_users_page():
    if not auth._admin():
        return redirect("/login")
    return send_from_directory(".", "plant_user_admin.html")


@app.get("/api/admin/plants")
def deployed_admin_plants():
    return auth.admin_plants()


@app.post("/api/admin/plant-users")
def deployed_create_plant_user():
    return auth.create_plant_user()


@app.post("/api/admin/plant-user-password")
def deployed_change_plant_user_password():
    return auth.change_plant_user_password()


@app.get("/api/my-plants")
def deployed_my_plants():
    return auth.my_plants()


# Add a direct entry to the existing Command Centre navigation.
# This is presentation-only; the destination remains server-authorized.
@app.after_request
def add_plant_user_management_nav(response):
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "text/html" not in content_type:
        return response

    try:
        html = response.get_data(as_text=True)
        marker = '<div class="nav-title">SYSTEM</div>'
        button = '''<button type="button" id="plantUserManagementNav" onclick="window.location.href='/account/create'">🏭 Plant & User Management</button>'''
        if marker in html and 'id="plantUserManagementNav"' not in html:
            html = html.replace(marker, marker + "\n" + button, 1)
            response.set_data(html)
    except Exception:
        # Never break the production page because of a presentation enhancement.
        pass
    return response


__all__ = [
    "deployed_session_context",
    "deployed_admin_users_page",
    "deployed_admin_plants",
    "deployed_create_plant_user",
    "deployed_change_plant_user_password",
    "deployed_my_plants",
    "add_plant_user_management_nav",
]
