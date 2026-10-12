from field_report_persistent_bridge import _best_report


def test_complete_report_beats_newer_sparse_duplicate():
    sparse_newer = {
        "report_id": "PM-RECENT-SPARSE",
        "tag": "PT_303",
        "source": "technician field report",
        "parsed_report": {
            "observation": "",
            "finding": "",
            "maintenance_action": "inspected",
            "outcome": "indication restored",
            "spare_used": "",
        },
    }
    complete_older = {
        "report_id": "PM-COMPLETE",
        "tag": "PT_303",
        "source": "technician field report",
        "parsed_report": {
            "observation": "abnormal pressure indication",
            "finding": "pressure transmitter faulty",
            "maintenance_action": "inspected and replaced transmitter",
            "outcome": "healthy pressure indication restored",
            "spare_used": "PT-303 x1",
            "recovery_status": "Recovered",
            "verification_status": "PENDING_VERIFICATION",
        },
    }
    selected = _best_report(
        "Show the saved field report for PT_303",
        [sparse_newer, complete_older],
        tag="PT-303",
    )
    assert selected["report_id"] == "PM-COMPLETE"


def test_requested_tag_never_falls_back_to_another_instrument():
    other_tag = {
        "report_id": "PM-PT519",
        "tag": "PT_519",
        "source": "technician field report",
        "observation": "other instrument observation",
        "maintenance_action": "checked",
    }
    assert _best_report(
        "Show the saved field report for PT_303",
        [other_tag],
        tag="PT-303",
    ) is None
