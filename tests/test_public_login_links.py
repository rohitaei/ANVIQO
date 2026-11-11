import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_landing_page_login_links_are_same_origin():
    html = (ROOT / "anviqo_public_website_index.html").read_text(encoding="utf-8")
    assert html.count('href="/login"') == 3
    assert "https://anviqo.onrender.com/login" not in html


def test_installed_app_command_centre_shortcut_is_same_origin():
    manifest = json.loads((ROOT / "anviqo-app.webmanifest").read_text(encoding="utf-8"))
    shortcut = next(item for item in manifest["shortcuts"] if item["name"] == "Enter Command Centre")
    assert shortcut["url"] == "/login"
    assert "anviqo.onrender.com" not in shortcut["url"]
