"""Lightweight compatibility entrypoint for ANVIQO.

Render starts this module directly. It intentionally avoids importing the full
ANVIQO Flask stack during Gunicorn startup so Render can detect the listening
HTTP port immediately. The full dashboard runtime is loaded only when a
non-health request arrives.

The public module also preserves the existing import surface through lazy
attribute forwarding.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from urllib.request import Request, urlopen

_FULL_MODULE = "failure_prediction_dashboard_full"
_PUBLIC_HOME = Path("anviqo_public_website_index.html")
_PUBLIC_MANIFEST = Path("anviqo-app.webmanifest")
_PUBLIC_SERVICE_WORKER = Path("anviqo-service-worker.js")
_APK_URL = "https://github.com/rohitaei/ANVIQO/releases/download/V2.0.0/ANVIQO-Android.apk"
_full = None


def _load():
    global _full
    if _full is None:
        _full = importlib.import_module(_FULL_MODULE)
    return _full


def __getattr__(name):
    return getattr(_load(), name)



def _health(environ, start_response):
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


def _public_file(path_obj, content_type, start_response):
    try:
        body = path_obj.read_bytes()
    except OSError:
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]
    start_response(
        "200 OK",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"),
        ],
    )
    return [body]


def _apk_download(environ, start_response):
    try:
        request = Request(_APK_URL, headers={"User-Agent": "ANVIQO-APK-Downloader/1.0"})
        with urlopen(request, timeout=30) as response:
            body = response.read()
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/vnd.android.package-archive"),
                ("Content-Disposition", 'attachment; filename="ANVIQO-Android.apk"'),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "public, max-age=3600"),
            ],
        )
        return [body]
    except Exception as exc:
        body = ("ANVIQO APK download temporarily unavailable: " + str(exc)).encode("utf-8")
        start_response("502 Bad Gateway", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if path == "/health" and method == "GET":
        return _health(environ, start_response)
    # The custom domain is the public ANVIQO website first. Keep the existing
    # authenticated application at / and /login behind its normal login flow.
    if method == "GET" and path == "/":
        return _public_file(_PUBLIC_HOME, "text/html; charset=utf-8", start_response)
    if method == "GET" and path == "/anviqo-app.webmanifest":
        return _public_file(_PUBLIC_MANIFEST, "application/manifest+json; charset=utf-8", start_response)
    if method == "GET" and path == "/anviqo-service-worker.js":
        return _public_file(_PUBLIC_SERVICE_WORKER, "application/javascript; charset=utf-8", start_response)
    if method == "GET" and path == "/download/anviqo.apk":
        return _apk_download(environ, start_response)
    return _load().app.wsgi_app(environ, start_response)


# Gunicorn target remains failure_prediction_dashboard_runtime:app.
# This callable is deliberately lazy and health-first.
app = application
