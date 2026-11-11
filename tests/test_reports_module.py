from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import field_report_persistent_bridge as bridge


def test_reports_module_has_filters_generation_and_download_exports():
    html = (ROOT / "anviqo_dashboard.html").read_text(encoding="utf-8")
    assert 'id="reportType"' in html
    assert 'id="reportFrom"' in html
    assert 'id="reportTo"' in html
    assert 'id="reportTag"' in html
    assert 'id="reportArea"' in html
    assert 'onclick="generateReport()"' in html
    assert "exportReport('txt')" in html
    assert "exportReport('html')" in html
    assert 'onclick="printReport()"' in html


def test_reports_prompt_is_selected_plant_scoped_and_evidence_gated():
    html = (ROOT / "anviqo_dashboard.html").read_text(encoding="utf-8")
    start = html.index("async function generateReport(){")
    end = html.index("\nfunction exportReport(", start)
    generator = html[start:end]
    assert "authenticated selected plant only" in generator
    assert "Never invent measurements" in generator
    assert "NO MATCHING EVIDENCE" in generator
    assert "PLC writes and SCADA control remain blocked" in generator


def test_report_export_is_disabled_until_successful_generation():
    html = (ROOT / "anviqo_dashboard.html").read_text(encoding="utf-8")
    assert 'id="exportReportTxt" disabled' in html
    assert 'id="exportReportHtml" disabled' in html
    assert "generatedReportText='';" in html
    assert "No report was exported." in html


def test_saved_field_report_answer_includes_action_outcome_recovery_and_verification():
    answer = bridge._format_report_answer({
        "tag": "PT-303",
        "observation": "No indication",
        "finding": "Fuse blown",
        "maintenance_action": "Fuse replaced",
        "outcome": "Signal returned to normal",
        "recovery_status": "Recovered",
        "spare_used": "Fuse 2A x 1",
        "verification_status": "PENDING_VERIFICATION",
        "created_at": "2026-11-11T12:00:00Z",
    })
    for detail in (
        "PT-303", "No indication", "Fuse blown", "Fuse replaced",
        "Signal returned to normal", "Recovered", "Fuse 2A x 1",
        "PENDING_VERIFICATION", "2026-11-11T12:00:00Z",
    ):
        assert detail in answer
    assert "not be treated as a verified fault diagnosis" in answer


def test_verified_field_report_is_not_marked_pending():
    answer = bridge._format_report_answer({
        "tag": "PT-303",
        "source": "technician field report",
        "verification_status": "VERIFIED",
    })
    assert "Verification: VERIFIED" in answer
    assert "PENDING_VERIFICATION; it must not be treated" not in answer
