from field_report_runtime import _report_query


def test_general_event_story_is_not_misrouted_to_field_report():
    assert _report_query("What happened around PT-303?") is False
    assert _report_query("What happened yesterday around PT-303?") is False


def test_explicit_saved_field_report_queries_are_routed():
    assert _report_query("Show the saved field report for PT_303") is True
    assert _report_query("Show recent field reports for PT-303") is True
    assert _report_query("What field reports mention PT-303?") is True
    assert _report_query("What did maintenance find last time on PT-303?") is True
