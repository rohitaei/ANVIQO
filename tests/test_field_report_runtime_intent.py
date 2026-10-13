from field_report_runtime import _report_query


def test_general_event_story_is_not_misrouted_to_field_report():
    assert _report_query("What happened around PT-303?") is False
    assert _report_query("What happened yesterday around PT-303?") is False


def test_explicit_saved_field_report_queries_are_routed():
    assert _report_query("Show the saved field report for PT_303") is True
    assert _report_query("Show recent field reports for PT-303") is True
    assert _report_query("What field reports mention PT-303?") is True
    assert _report_query("What did maintenance find last time on PT-303?") is True

from field_report_runtime import _report_match_score


def test_complete_exact_tag_report_outranks_sparse_duplicate():
    question = "Show the saved field report for PT_303"
    sparse = {
        "report_id": "PM-RECENT-SPARSE",
        "tag": "PT_303",
        "source": "technician field report",
        "parsed_report": {
            "source": "technician field report",
            "maintenance_action": "inspected",
            "outcome": "indication restored",
        },
    }
    complete = {
        "report_id": "PM-COMPLETE",
        "tag": "PT_303",
        "source": "technician field report",
        "parsed_report": {
            "source": "technician field report",
            "observation": "abnormal pressure indication",
            "finding": "pressure transmitter faulty",
            "maintenance_action": "inspected and replaced transmitter",
            "outcome": "healthy pressure indication restored",
            "spare_used": "PT-303 x1",
            "recovery_status": "Recovered",
            "verification_status": "PENDING_VERIFICATION",
        },
    }
    assert _report_match_score(complete, question, "PT-303") > _report_match_score(
        sparse, question, "PT-303"
    )


def test_runtime_score_never_prefers_wrong_tag_over_requested_tag():
    question = "Show the saved field report for PT_303"
    requested = {
        "tag": "PT_303",
        "source": "technician field report",
        "observation": "pressure transmitter faulty",
    }
    wrong_tag = {
        "tag": "PT_519",
        "source": "technician field report",
        "observation": "abnormal pressure indication, transmitter faulty",
        "maintenance_action": "replaced transmitter",
        "outcome": "restored",
        "spare_used": "PT-519 x1",
    }
    assert _report_match_score(requested, question, "PT-303") > _report_match_score(
        wrong_tag, question, "PT-303"
    )
