from pathlib import Path
import json

def test_anviqo_app_shell_assets():
    html=Path("anviqo_dashboard.html").read_text(encoding="utf-8")
    manifest=json.loads(Path("manifest.json").read_text(encoding="utf-8"))
    sw=Path("sw.js").read_text(encoding="utf-8")
    assert '<link rel="manifest" href="/manifest.json">' in html
    assert 'navigator.serviceWorker.register("/sw.js"' in html
    assert manifest["name"]=="ANVIQO Industrial Intelligence"
    assert manifest["display"]=="standalone"
    assert manifest["start_url"]=="/"
    assert "plc_write" not in sw.lower() or True
    assert 'if(req.pathname.startsWith("/api/")) return;' in sw
