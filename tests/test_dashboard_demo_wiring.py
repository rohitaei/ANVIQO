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
                 "maintenance", "management", "interlocks"):
        assert f"{page}:" in loader, f"{page} page has no explicit evidence query"
    assert "if(name==='spares'){await loadSpares();return;}" in loader
    assert "if(name==='system')await loadSystem();" in loader


def test_events_and_what_changed_use_the_selected_plant_v2_stream():
    html = _dashboard()
    start = html.index("async function loadPage(name){")
    end = html.index("\\nasync function loadCommandCentreStream", start)
    loader = html[start:end]
    assert "if(name==='events'||name==='changed')" in loader
    assert "await loadCommandCentreStream(name)" in loader
    assert "events:['eventData'" not in loader
    assert "changed:['changedData'" not in loader
    start = html.index("async function loadCommandCentreStream(mode){")
    end = html.index("\\nasync function loadAskInto", start)
    stream = html[start:end]
    assert "fetch('/api/command-centre/stream'" in stream
    assert "data.scope!=='SELECTED_PLANT_ONLY'" in stream
    assert "data.events" in stream and "data.changes" in stream
    assert "No other plant data was substituted." in stream


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
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", _dashboard(), re.I | re.S)
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


def test_field_report_user_content_is_html_escaped():
    html = _dashboard()
    start = html.index("async function submitFieldReport(){")
    end = html.index("\n}\n\n</script>", start)
    renderer = html[start:end]
    for field in ("data.status", "p.equipment", "p.tag", "p.area", "p.observation",
                  "p.finding", "p.maintenance_action", "p.outcome", "p.recovery_status"):
        assert f"escapeHtml({field}" in renderer
    assert "escapeHtml(err.message || err)" in renderer


def test_spare_search_uses_shared_api_error_and_auth_handling():
    html = _dashboard()
    start = html.index("async function searchSpares(){")
    end = html.index("\\n}\\n\\n</script>", start)
    search = html[start:end]
    assert "await askAPI(" in search
    assert "fetch('/api/ask'" not in search
    assert "escapeHtml(d.answer" in search


def test_dashboard_api_helper_surfaces_non_success_responses():
    html = _dashboard()
    start = html.index("async function api(url,options){")
    end = html.index("\\nfunction box", start)
    helper = html[start:end]
    assert "if(!r.ok)throw Error(data.message||data.error||('Request failed: HTTP '+r.status));" in helper


def test_overview_clears_stale_metrics_when_api_fails():
    html = _dashboard()
    start = html.index("async function refresh(){")
    end = html.index("\\nasync function loadPage", start)
    refresh = html[start:end]
    assert "['health','alarms','critical','events','ioCount']" in refresh
    assert "Selected-plant overview unavailable:" in refresh
