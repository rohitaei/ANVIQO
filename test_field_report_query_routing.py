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
