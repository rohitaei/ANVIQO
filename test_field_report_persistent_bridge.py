import field_report_persistent_bridge as bridge
import field_report_runtime as runtime


def test_best_report_prefers_exact_tag_and_field_report():
    reports = [
        {
            "memory_id": "PM-OTHER",
            "tag": "PT-304",
            "source": "technician field report",
            "observation": "different issue",
        },
        {
            "memory_id": "PM-PT303",
            "tag": "PT-303",
            "source": "technician field report",
            "observation": "No indication",
            "finding": "Fuse blown",
            "maintenance_action": "Fuse replaced",
        },
    ]
    result = bridge._best_report("What happened to PT-303 last time?", reports, tag="PT-303")
    assert result["memory_id"] == "PM-PT303"


def test_best_report_ignores_non_field_report_sources():
    reports = [
        {"memory_id": "PM-1", "tag": "PT-303", "source": "SCADA", "observation": "alarm"},
        {"memory_id": "PM-2", "tag": "PT-303", "source": "technician field report", "observation": "No indication"},
    ]
    result = bridge._best_report("What happened to PT-303?", reports, tag="PT-303")
    assert result["memory_id"] == "PM-2"


def test_best_report_uses_nested_parsed_report_payload():
    reports = [
        {
            "report_id": "FR-PT303",
            "tag": "PT-303",
            "source": "technician field report",
            "parsed_report": {
                "tag": "PT-303",
                "observation": "No indication",
                "finding": "Fuse blown / no power",
                "maintenance_action": "Fuse replaced",
                "outcome": "Instrument returned to normal operation",
                "spare_used": "",
                "verification_status": "PENDING_VERIFICATION",
                "source": "technician field report",
            },
        }
    ]
    result = bridge._best_report("What happened to PT303?", reports, tag="PT303")
    view = bridge._report_view(result)
    assert view["observation"] == "No indication"
    assert view["finding"] == "Fuse blown / no power"
    assert view["maintenance_action"] == "Fuse replaced"
    assert view["outcome"] == "Instrument returned to normal operation"


def test_empty_field_report_placeholder_is_not_usable():
    assert runtime._has_report_details({"source": "technician field report", "tag": "PT-303"}) is False
    assert runtime._has_report_details({"source": "technician field report", "tag": "PT-303", "finding": "Fuse blown"}) is True



def test_authenticated_session_without_user_id_still_intercepts_report_query(monkeypatch):
    """A valid tenant session must not fall through to generic PCI knowledge."""
    from flask import session

    monkeypatch.setattr(bridge, "_field_reports_from_neon", lambda tag="", limit=20: [])
    app = bridge.app
    with app.test_request_context(
        "/api/ask",
        method="POST",
        json={"question": "Show the saved field report for PT_303"},
    ):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        session["plant_id"] = "QA-PLANT-ONLY"
        # Intentionally omit user_id: some authenticated session paths do not
        # populate it, but still carry the selected tenant.
        result = bridge.persistent_field_report_query_bridge()

    assert result is not None
    response, status_code = result if isinstance(result, tuple) else (result, 200)
    payload = response.get_json()
    assert status_code == 200
    assert payload["status"] == "NOT_FOUND"
    assert payload["requested_tag"] == "PT-303"
    assert payload["evidence"] is None
    assert "will not substitute PCI identity" in payload["answer"]
    assert payload["read_only"] is True
    assert payload["plc_write"] is False
    assert payload["scada_control"] is False
    assert payload["automatic_execution"] is False
    assert payload["human_decision_required"] is True


def test_authenticated_report_query_fails_closed_without_selected_plant():
    from flask import session

    app = bridge.app
    with app.test_request_context(
        "/api/ask",
        method="POST",
        json={"question": "Show the saved field report for PT_303"},
    ):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        # No selected plant must not trigger a global or cross-plant lookup.
        result = bridge.persistent_field_report_query_bridge()

    response, status_code = result if isinstance(result, tuple) else (result, 200)
    payload = response.get_json()
    assert status_code == 503
    assert payload["status"] == "TENANT_CONTEXT_UNAVAILABLE"
    assert payload["plc_write"] is False
    assert payload["scada_control"] is False



def test_persisted_raw_report_renders_all_fields_without_inventing_missing_details(monkeypatch):
    from flask import session

    report = {
        "report_id": "QA-PT303-RAW",
        "tag": "PT-303",
        "source": "technician field report",
        "raw_report": "Pt-303 was faulty changed by new 1nos spare now ok",
        "maintenance_action": "Pt-303 was faulty changed by new 1nos spare now ok",
        "outcome": "Pt-303 was faulty changed by new 1nos spare now ok",
        "verification_status": "PENDING_VERIFICATION",
        "organization_id": "QA-ORG-ONLY",
        "plant_id": "QA-PLANT-ONLY",
        "parsed_report": {
            "tag": "PT-303",
            "source": "technician field report",
            "raw_report": "Pt-303 was faulty changed by new 1nos spare now ok",
            "maintenance_action": "Pt-303 was faulty changed by new 1nos spare now ok",
            "outcome": "Pt-303 was faulty changed by new 1nos spare now ok",
            "spare_used": "",
            "observation": "",
            "finding": "",
            "verification_status": "PENDING_VERIFICATION",
        },
    }
    monkeypatch.setattr(bridge, "_field_reports_from_neon", lambda tag="", limit=20: [report])
    app = bridge.app
    with app.test_request_context(
        "/api/ask",
        method="POST",
        json={"question": "Show the saved field report for PT_303"},
    ):
        session["authenticated"] = True
        session["organization_id"] = "QA-ORG-ONLY"
        session["plant_id"] = "QA-PLANT-ONLY"
        result = bridge.persistent_field_report_query_bridge()

    response, status_code = result if isinstance(result, tuple) else (result, 200)
    payload = response.get_json()
    answer = payload["answer"]
    assert status_code == 200
    assert payload["status"] == "OK"
    assert payload["source"] == "technician field report"
    assert "Reported problem: Pt-303 was faulty" in answer
    assert "Observation: Not separately recorded" in answer
    assert "Finding: Not separately recorded" in answer
    assert "Maintenance action: changed by new 1nos spare" in answer
    assert "Spare used: One new spare is mentioned; exact spare tag/type is not recorded" in answer
    assert "Outcome: Technician reported: now ok" in answer
    assert "Verification status: PENDING_VERIFICATION" in answer
    assert "Original technician text: Pt-303 was faulty changed by new 1nos spare now ok" in answer
    assert payload["read_only"] is True
    assert payload["plc_write"] is False
    assert payload["scada_control"] is False
    assert payload["automatic_execution"] is False
    assert payload["human_decision_required"] is True
