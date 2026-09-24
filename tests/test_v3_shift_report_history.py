from v2.shift_report_adapter import parse_shift_report_text
from v3.shift_report_history import (
    persist_shift_report_history,
    validate_shift_report_tag_evidence,
)


REPORT = """DATE\t09/23/2026
1 Hr. Avg. Value\tPT_303\tPT_304\tTE_301
00:00Hrs - 1:00Hrs\t7.333333492\t0.0802083388\t40.60000229
1:00Hrs - 2:00Hrs\t6.837384224\t5.324073792\t40.90000153
2:00Hrs - 3:00Hrs\t6.736110687\t1.171875\t41.20000076
"""


def test_alpha31_persists_shift_report_through_tenant_boundary(monkeypatch):
    calls = []

    def fake_record(**kwargs):
        calls.append(kwargs)
        point = kwargs["point"]
        return {
            "plant_id": kwargs["plant_id"],
            "organization_id": kwargs["organization_id"],
            "tag": point.tag,
            "value": point.value,
            "timestamp": point.timestamp,
            "source": point.source,
            "provenance": kwargs["provenance"],
        }

    monkeypatch.setattr(
        "failure_prediction_history.record_tenant_industrial_point",
        fake_record,
    )

    result = persist_shift_report_history(
        "plant-a",
        "org-a",
        REPORT,
        provenance="Tata Metaliks supplied report 2026-09-23",
    )

    assert result["points_parsed"] == 9
    assert result["points_persisted"] == 9
    assert all(call["plant_id"] == "plant-a" for call in calls)
    assert all(call["organization_id"] == "org-a" for call in calls)
    assert all(call["source_type"] == "HISTORICAL_ARCHIVE" for call in calls)
    assert calls[0]["point"].mode == "HISTORICAL"
    assert calls[0]["point"].source == "TATA METALIKS SHIFT MATERIAL REPORT"


def test_alpha31_preserves_pt303_and_pt304_history(monkeypatch):
    saved = []

    def fake_record(**kwargs):
        point = kwargs["point"]
        saved.append(point)
        return {"tag": point.tag, "value": point.value, "timestamp": point.timestamp}

    monkeypatch.setattr(
        "failure_prediction_history.record_tenant_industrial_point",
        fake_record,
    )

    persist_shift_report_history("plant-a", "org-a", REPORT)

    pt303 = [p for p in saved if p.tag == "PT_303"]
    pt304 = [p for p in saved if p.tag == "PT_304"]
    assert [p.value for p in pt303] == [7.333333492, 6.837384224, 6.736110687]
    assert [p.value for p in pt304] == [0.0802083388, 5.324073792, 1.171875]
    assert [p.timestamp for p in pt303] == [
        "2026-09-23T00:00:00+00:00",
        "2026-09-23T01:00:00+00:00",
        "2026-09-23T02:00:00+00:00",
    ]


def test_alpha31_requires_both_tenant_identifiers():
    try:
        persist_shift_report_history("plant-a", "", REPORT)
    except ValueError as exc:
        assert "plant_id and organization_id" in str(exc)
    else:
        raise AssertionError("missing organization_id must be rejected")


def test_alpha31_reuses_canonical_evidence_gate():
    observations = [
        {"plant_id": "plant-a", "tag": "PT-303", "timestamp": "2026-09-23T00:00:00+00:00", "value": 7.3},
        {"plant_id": "plant-a", "tag": "PT-303", "timestamp": "2026-09-23T01:00:00+00:00", "value": 6.8},
    ]
    result = validate_shift_report_tag_evidence("plant-a", "PT-303", observations)
    assert result["quality"] == "VALID"
    assert result["usable_observation_count"] == 2
    assert result["safety"]["read_only"] is True
    assert result["safety"]["plc_write"] is False
