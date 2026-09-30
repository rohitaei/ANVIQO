"""Lightweight Render WSGI entrypoint.

Render must be able to probe the web port before the full ANVIQO Flask
application is imported. Health requests therefore return directly from this
small module; all other requests are delegated lazily to the existing ANVIQO
runtime. No plant intelligence or PLC/SCADA behavior is changed.
"""
from __future__ import annotations

_app = None


def _load_app():
    global _app
    if _app is None:
        from failure_prediction_dashboard_runtime import app
        _app = app
    return _app


def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/health" and method == "GET":
        body = b'{"status":"ok","service":"ANVIQO","health_check":true}'
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]

    return _load_app().wsgi_app(environ, start_response)


app = application
