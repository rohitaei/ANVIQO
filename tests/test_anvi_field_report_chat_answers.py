import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, session

import anvi_neon_store
import field_report_runtime as runtime


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "anvi_field_reports_10.json"


@pytest.fixture
def qa_reports():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["not_for_production"] is True
    return payload["reports"]


def test_ten_qa_reports_are_distinct_and_tenant_scoped(qa_reports):
    assert len(qa_reports) == 10
    assert len({r["report_id"] for r in qa_reports}) == 10
    assert len({r["tag"] for r in qa_reports}) == 10
    assert all(r["organization_id"] == "QA-ORG-ONLY" for r in qa_reports)
    assert all(r["plant_id"] == "QA-PLANT-ONLY" for r in qa_reports)


def test_ten_nested_reports_save_and_answer_for_exact_equipment(monkeypatch, qa_reports):
    """Exercise the persistence payload shape and the same answer function used by /api/ask."""
    saved = {}
    app = Flask(__name__)
    app.secret_key = "field-report-test-only"

    def fake_exec(sql, params=(), fetch=False):
        if "INSERT INTO anviqo_field_reports" in sql:
            saved[str(params[0])] = json.loads(params[3])
            return None
        if fetch:
            return [(row,) for row in saved.values()]
        return None

    monkeypatch.setattr(anvi_neon_store, "neon_enabled", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "init_neon", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)

    with app.test_request_context("/api/field_report", method="POST"):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        session["plant_id"] = "QA-PLANT-ONLY"
        for report in qa_reports:
            assert anvi_neon_store.upsert_field_report(report) is True

    assert len(saved) == 10
    assert all(r["organization_id"] == "QA-ORG-ONLY" for r in saved.values())
    assert all(r["plant_id"] == "QA-PLANT-ONLY" for r in saved.values())

    # Simulate the tenant-filtered persistent query returning stored payloads.
    def fetch_reports(tag="", limit=20):
        rows = [
            r for r in saved.values()
            if r.get("organization_id") == "QA-ORG-ONLY"
            and r.get("plant_id") == "QA-PLANT-ONLY"
        ]
        if tag:
            normalized = "".join(ch.lower() for ch in tag if ch.isalnum())
            rows = [r for r in rows if "".join(ch.lower() for ch in r.get("tag", "") if ch.isalnum()) == normalized]
        return rows[:limit]

    import sys
    monkeypatch.setitem(sys.modules, "field_report_persistent_bridge",
                        SimpleNamespace(_field_reports_from_neon=fetch_reports))
    monkeypatch.setattr(runtime, "_authenticated_tenant",
                        lambda: ("QA-PLANT-ONLY", "QA-ORG-ONLY"))

    for report in qa_reports:
        question = f"What happened to {report['tag']} in the field report?"
        answer = runtime.answer_field_report_query(question)
        assert answer is not None, report["tag"]
        assert answer["status"] == "OK"
        assert answer["domain"] == "plant_memory"
        assert answer["source"] == "technician field report"
        assert answer["evidence"]["tag"] == report["tag"]
        assert report["observation"] in answer["answer"]
        assert report["finding"] in answer["answer"]
        assert report["maintenance_action"] in answer["answer"]
        assert report["outcome"] in answer["answer"]
        assert answer["read_only"] is True
        assert answer["plc_write"] is False
        assert answer["scada_control"] is False
        assert answer["automatic_execution"] is False
        assert answer["human_decision_required"] is True


def test_nested_report_fields_are_flattened_for_answer():
    raw = {
        "report_id": "QA-FR-NESTED",
        "source": "technician field report",
        "parsed_report": {
            "tag": "PT-303",
            "observation": "Indication absent",
            "finding": "Fuse found open",
            "maintenance_action": "Fuse replaced under approved isolation",
            "outcome": "Local indication returned",
            "source": "technician field report",
        },
    }
    view = runtime._flatten_report(raw)
    assert runtime._has_report_details(raw)
    assert view["tag"] == "PT-303"
    assert view["observation"] == "Indication absent"
    assert view["finding"] == "Fuse found open"
    assert view["maintenance_action"] == "Fuse replaced under approved isolation"
    assert view["outcome"] == "Local indication returned"


def test_missing_requested_tag_does_not_answer_from_another_report(monkeypatch, qa_reports):
    import sys
    monkeypatch.setitem(
        sys.modules, "field_report_persistent_bridge",
        SimpleNamespace(_field_reports_from_neon=lambda tag="", limit=20: qa_reports[:1]),
    )
    monkeypatch.setattr(runtime, "_authenticated_tenant",
                        lambda: ("QA-PLANT-ONLY", "QA-ORG-ONLY"))
    answer = runtime.answer_field_report_query("What happened to PT-999 in the field report?")
    assert answer is None


def test_report_history_question_requires_evidence_not_invented_answer(monkeypatch):
    import sys
    monkeypatch.setitem(
        sys.modules, "field_report_persistent_bridge",
        SimpleNamespace(_field_reports_from_neon=lambda tag="", limit=20: []),
    )
    monkeypatch.setattr(runtime, "_authenticated_tenant",
                        lambda: ("QA-PLANT-ONLY", "QA-ORG-ONLY"))
    assert runtime.answer_field_report_query("What happened to PT-303 last time?") is None


def test_tenantless_session_never_uses_global_memory(monkeypatch):
    monkeypatch.setattr(runtime, "_authenticated_tenant", lambda: (None, None))
    # Tenantless behavior remains the existing local Plant Memory path; this
    # test guards that the durable tenant bridge is not silently selected.
    called = {"persistent": False}
    import sys
    monkeypatch.setitem(
        sys.modules, "field_report_persistent_bridge",
        SimpleNamespace(_field_reports_from_neon=lambda **kwargs: called.update(persistent=True) or []),
    )
    monkeypatch.setattr("plant_memory.search_all_memory", lambda **kwargs: [])
    assert runtime.answer_field_report_query("What happened to PT-303 last time?") is None
    assert called["persistent"] is False
