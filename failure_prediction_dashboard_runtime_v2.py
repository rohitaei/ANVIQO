"""ANVIQO dashboard response wrapper.

Serves the authenticated Command Centre dashboard as a normal buffered HTML
response before Flask's send_from_directory handler can mark it direct-pass-
through. Reuses the existing V1.2 demo injection logic and does not modify V5.
"""
from __future__ import annotations

from flask import make_response, redirect, request, session, send_from_directory

from failure_prediction_dashboard_runtime import (
    app,
    inject_prediction_demo_dashboard,
)

VERSION = "ANVIQO-FP-DEMO-DASHBOARD-V1.3"


@app.before_request
def serve_buffered_dashboard():
    """Return an injected, buffered dashboard response for authenticated users."""
    if request.method != "GET" or request.path != "/":
        return None
    if not session.get("authenticated"):
        return redirect("/login")
    try:
        with open("anviqo_dashboard.html", "r", encoding="utf-8") as handle:
            html = handle.read()
        html = inject_prediction_demo_dashboard(html)
        response = make_response(html, 200)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers.pop("ETag", None)
        response.headers.pop("Last-Modified", None)
        return response
    except Exception:
        return None
