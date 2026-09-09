"""Prepare the Command Centre HTML with the Failure Prediction demo panel.

This runs once at service startup and writes the panel directly into the
served dashboard HTML. It does not touch frozen V5 intelligence or plant
control paths.
"""
from pathlib import Path

from failure_prediction_dashboard_runtime import PANEL_HTML, SCRIPT

DASHBOARD = Path("anviqo_dashboard.html")
MARKER = 'id="anviqoFpDemo"'
BODY = "</body>"


def main() -> None:
    html = DASHBOARD.read_text(encoding="utf-8")
    if MARKER in html:
        print("Failure Prediction panel already present in dashboard HTML")
        return
    idx = html.lower().rfind(BODY)
    if idx < 0:
        raise RuntimeError("Dashboard HTML has no closing body tag")
    updated = html[:idx] + "\n" + PANEL_HTML + "\n" + SCRIPT + "\n" + html[idx:]
    DASHBOARD.write_text(updated, encoding="utf-8")
    print("Failure Prediction panel written directly into dashboard HTML")


if __name__ == "__main__":
    main()
