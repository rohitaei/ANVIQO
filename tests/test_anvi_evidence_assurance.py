from datetime import datetime, timezone, timedelta

from anvi_evidence_assurance import build_evidence_assurance


def _snapshot():
    now = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
    return {
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
        "timestamp": now.isoformat(),
        "total_io": 4,
        "healthy": 2,
        "warning": 1,
        "critical": 1,
        "active_events": 2,
        "changed": 1,
        "plant_health_score": 62.5,
        "points": [
            {"tag": "PT-1", "state": "HEALTHY"},
            {"tag": "PT-2", "state": "HEALTHY", "changed": True},
            {"tag": "PT-3", "state": "WARNING", "event_active": True},
            {"tag": "PT-4", "state": "CRITICAL", "event_active": True},
        ],
    }


def test_consistent_simulation_snapshot_gets_transparent_assurance():
    now = datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc)
    result = build_evidence_assurance(_snapshot(), plant_id="p1", organization_id="o1", now=now)
    assert result["assurance_status"] == "CONSISTENT_SIMULATION_EVIDENCE"
    assert result["checks"]["point_total_reconciled"] is True
    assert result["checks"]["event_count_reconciled"] is True
    assert result["checks"]["changed_count_reconciled"] is True
    assert result["recomputed_health_score"] == 62.5
    assert "SIMULATION_NOT_LIVE_TELEMETRY" in result["findings"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False


def test_mismatched_counters_are_disclosed_not_silently_averaged():
    snapshot = _snapshot()
    snapshot["active_events"] = 9
    snapshot["plant_health_score"] = 99.0
    result = build_evidence_assurance(
        snapshot,
        now=datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc),
    )
    assert result["assurance_status"] == "PARTIAL_OR_INCONSISTENT_EVIDENCE"
    assert "ACTIVE_EVENT_COUNT_MISMATCH" in result["findings"]
    assert "PLANT_HEALTH_SCORE_MISMATCH" in result["findings"]


def test_onboarding_data_is_never_described_as_live_telemetry():
    snapshot = _snapshot()
    snapshot["mode"] = "ONBOARDING_DATA"
    result = build_evidence_assurance(
        snapshot,
        now=datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc),
    )
    assert result["assurance_status"] == "CONSISTENT_ONBOARDING_DATA"
    assert "ONBOARDING_DATA_NOT_LIVE_TELEMETRY" in result["findings"]


def test_stale_snapshot_is_flagged():
    now = datetime(2026, 11, 14, 0, 10, tzinfo=timezone.utc)
    result = build_evidence_assurance(_snapshot(), now=now, freshness_seconds=60)
    assert result["checks"]["snapshot_fresh"] is False
    assert "SNAPSHOT_STALE" in result["findings"]


def test_missing_snapshot_returns_partial_not_fake_health():
    result = build_evidence_assurance(None)
    assert result["assurance_status"] == "PARTIAL_OR_INCONSISTENT_EVIDENCE"
    assert result["recomputed_health_score"] is None
    assert "NO_POINT_EVIDENCE" in result["findings"]



def test_selected_plant_snapshot_cache_is_tenant_scoped_and_returns_copies(monkeypatch):
    import anvi_universal_command_centre as adapter
    from flask import Flask, session

    app = Flask(__name__)
    app.secret_key = "test-only"
    calls = []

    def fake_builder(plant_id):
        calls.append((session.get("organization_id"), plant_id))
        return {
            "mode": "SIMULATION",
            "source": "TEST",
            "points": [{"tag": "PT-1", "state": "HEALTHY"}],
        }

    monkeypatch.setattr(adapter, "_build_tenant_snapshot", fake_builder)
    adapter._TENANT_SNAPSHOT_CACHE.clear()
    try:
        with app.test_request_context("/"):
            session["organization_id"] = "org-a"
            first = adapter._tenant_snapshot("plant-a")
            first["points"][0]["state"] = "MUTATED"
            second = adapter._tenant_snapshot("plant-a")
            assert second["points"][0]["state"] == "HEALTHY"
            assert len(calls) == 1

            session["organization_id"] = "org-b"
            adapter._tenant_snapshot("plant-a")
            assert len(calls) == 2
    finally:
        adapter._TENANT_SNAPSHOT_CACHE.clear()



def test_reported_state_totals_must_match_point_level_evidence():
    snapshot = _snapshot()
    snapshot["critical"] = 7
    result = build_evidence_assurance(
        snapshot,
        now=datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc),
    )
    assert result["checks"]["state_counts_reconciled"] is False
    assert "STATE_COUNT_MISMATCH" in result["findings"]
    assert result["assurance_status"] == "PARTIAL_OR_INCONSISTENT_EVIDENCE"



def test_area_rollups_must_reconcile_with_point_evidence():
    snapshot = _snapshot()
    snapshot["areas"] = [{
        "name": "GENERAL", "count": 5,
        "healthy": 2, "warning": 1, "critical": 1,
    }]
    result = build_evidence_assurance(
        snapshot,
        now=datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc),
    )
    assert result["checks"]["area_total_reconciled"] is False
    assert "AREA_TOTAL_MISMATCH" in result["findings"]
    assert result["assurance_status"] == "PARTIAL_OR_INCONSISTENT_EVIDENCE"


def test_area_state_counts_must_match_each_area():
    snapshot = _snapshot()
    snapshot["areas"] = [{
        "name": "GENERAL", "count": 4,
        "healthy": 2, "warning": 0, "critical": 2,
    }]
    result = build_evidence_assurance(
        snapshot,
        now=datetime(2026, 11, 14, 0, 0, 5, tzinfo=timezone.utc),
    )
    assert result["checks"]["area_state_counts_reconciled"] is False
    assert "AREA_STATE_COUNT_MISMATCH" in result["findings"]
