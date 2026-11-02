"""Regression tests for Phase-2 field-report query routing.

The field-report bridge executes before /api/ask, so its classifier must not
capture ordinary spare/inventory commands.
"""

from field_report_runtime import _report_query


def test_plain_spare_use_is_not_a_field_report_query():
    assert _report_query("I used 1 PT-303 spare") is False


def test_plain_spare_consumption_is_not_a_field_report_query():
    assert _report_query("PT-303 spare consumed") is False


def test_plain_replacement_is_not_a_field_report_query():
    assert _report_query("I replaced PT-303") is False


def test_explicit_field_report_is_a_field_report_query():
    assert _report_query("Show me the field report for PT-303") is True


def test_historical_report_question_is_a_field_report_query():
    assert _report_query("What happened to PT-303 last time?") is True


def test_spare_used_inside_report_question_is_a_field_report_query():
    assert _report_query("What spare was used in the field report for PT-303?") is True


def test_authenticated_report_query_without_selected_plant_blocks_shared_memory(monkeypatch):
    from flask import Flask, session
    app = Flask(__name__)
    app.secret_key = "test-secret"

    def forbidden_shared_read(**kwargs):
        raise AssertionError("Shared Plant Memory must not be queried for authenticated users")

    monkeypatch.setattr("plant_memory.search_all_memory", forbidden_shared_read)
    with app.test_request_context("/api/ask"):
        session.update({"authenticated": True, "user_id": "user-1", "organization_id": "org-1"})
        result = field_report_runtime.answer_field_report_query("Show field report PT-303")
    assert result["status"] == "BLOCKED"
    assert result["evidence_status"] == "NO_AUTHORIZED_PLANT"


def test_authenticated_report_query_uses_selected_plant_store(monkeypatch):
    from flask import Flask, session
    app = Flask(__name__)
    app.secret_key = "test-secret"
    report = {
        "report_id": "PM-TENANT-003",
        "memory_id": "PM-TENANT-003",
        "tag": "PT-303",
        "equipment": "PT-303",
        "source": "technician field report",
        "observation": "No indication",
        "finding": "Fuse blown",
        "maintenance_action": "Fuse replaced",
        "outcome": "Signal restored",
        "verification_status": "PENDING_VERIFICATION",
    }

    def forbidden_shared_read(**kwargs):
        raise AssertionError("Shared Plant Memory must not be queried for authenticated tenants")

    monkeypatch.setattr("plant_memory.search_all_memory", forbidden_shared_read)
    monkeypatch.setattr(
        "field_report_persistent_bridge._field_reports_from_neon",
        lambda tag="", limit=20: [report],
    )
    with app.test_request_context("/api/ask"):
        session.update({
            "authenticated": True, "user_id": "user-1",
            "organization_id": "org-1", "plant_id": "plant-1"
        })
        result = field_report_runtime.answer_field_report_query("Show field report for PT-303")
    assert result["status"] == "OK"
    assert result["verification_status"] == "PENDING_VERIFICATION"
    assert "Fuse blown" in result["answer"]
