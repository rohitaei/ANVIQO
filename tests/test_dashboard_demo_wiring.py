from pathlib import Path
import re
import shutil
import subprocess

DASHBOARD = Path(__file__).resolve().parents[1] / "anviqo_dashboard.html"


def _dashboard():
    return DASHBOARD.read_text(encoding="utf-8")


def test_every_sidebar_page_has_a_matching_page_container():
    html = _dashboard()
    names = re.findall(r'data-page="([a-z0-9_-]+)"', html)
    assert names, "No sidebar pages found"
    for name in names:
        assert f'id="page-{name}"' in html, f"Missing page container for {name}"


def test_overview_io_count_targets_the_existing_element():
    html = _dashboard()
    assert "document.getElementById('ioCount')" in html
    assert "document.getElementById('totalIO')" not in html


def test_intelligence_pages_use_the_selected_plant_anvi_query_path():
    html = _dashboard()
    start = html.index("async function loadPage(name){")
    end = html.index("\nasync function loadAskInto", start)
    loader = html[start:end]
    for page in ("alarms", "analysis", "prediction", "critical", "equipment",
                 "maintenance", "management", "events", "changed", "interlocks"):
        assert f"{page}:" in loader, f"{page} page has no explicit evidence query"
    assert "if(name==='spares'){await loadSpares();return;}" in loader
    assert "if(name==='system')await loadSystem();" in loader


def test_spares_page_reads_structured_tenant_scoped_inventory_not_static_demo_api():
    html = _dashboard()
    start = html.index("async function loadSpares(){")
    end = html.index("\nasync function searchSpares(){", start)
    loader = html[start:end]
    assert "askAPI('Show critical spares inventory for the selected plant')" in loader
    assert "askAPI('Show low-stock critical spares for the selected plant')" in loader
    assert "all.domain!=='critical_spares'" in loader
    assert "fetch('/api/maintenance')" not in loader
    assert "No global or other-plant inventory was substituted." in loader


def test_system_status_displays_returned_state_and_safety_contract():
    html = _dashboard()
    start = html.index("async function loadSystem(){")
    end = html.index("\nlet recognition=null;", start)
    loader = html[start:end]
    for field in ("d.product", "d.version", "d.core", "d.status", "d.timestamp",
                  "safety.plc_write", "safety.scada_control",
                  "safety.automatic_authorization", "safety.human_decision_required"):
        assert field in loader


def test_interlocks_page_has_a_real_evidence_mount():
    html = _dashboard()
    assert 'id="interlocksData"' in html
    assert "interlocks:['interlocksData'" in html


def test_inline_javascript_parses_when_node_is_available():
    node = shutil.which("node")
    if not node:
        return
    scripts = re.findall(r"<script\\b[^>]*>(.*?)</script>", _dashboard(), re.I | re.S)
    assert scripts
    for index, script in enumerate(scripts):
        result = subprocess.run(
            [node, "--check"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Inline script {index} has a JavaScript syntax error:\\n{result.stderr}"
        )
