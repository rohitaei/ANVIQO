from datetime import datetime, timezone, timedelta

from anvi_v2_realtime_store import TelemetryPoint
from anvi_v3_unified_platform import UnifiedIndustrialPlatform, PlatformEvent, SAFETY


def test_unified_platform_composes_v2_v3_domains():
    p = UnifiedIndustrialPlatform()
    org, plant = "org-1", "plant-1"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=2)
    p.ingest(TelemetryPoint(org, plant, "PT-303", t0, 42.0, "bar", "GOOD", "SIMULATION", 1),
             selected_org=org, selected_plant=plant)
    p.ingest(TelemetryPoint(org, plant, "PT-303", t0 + timedelta(seconds=30), 68.0, "bar", "GOOD", "SIMULATION", 2),
             selected_org=org, selected_plant=plant)
    p.add_event(PlatformEvent(org, plant, "ALARM", "PT-303", t0 + timedelta(seconds=31),
                              "PT-303 warning state", "WARNING", equipment="PT-303"),
                selected_org=org, selected_plant=plant)
    assert p.what_changed(org, plant, "PT-303")["changes"][0]["delta"] == 26.0
    assert p.alarms(org, plant)["warning_count"] == 1
    assert p.instrument(org, plant, "PT-303")["health_flags"]["baseline_deviation"] is False
    assert p.equipment(org, plant, "PT-303")["risk_band"] == "WARNING"
    assert p.evidence_graph(org, plant, "PT-303")["causal_claimed"] is False
    assert p.maintenance(org, plant)["human_approval_required"] is True
    assert p.energy_production_quality(org, plant, ["PT-303"])["metrics"]["PT-303"]["latest"] == 68.0


def test_tenant_boundary_and_safety():
    p = UnifiedIndustrialPlatform()
    point = TelemetryPoint("foreign", "plant-x", "PT-303", datetime.now(timezone.utc), 1.0)
    try:
        p.ingest(point, selected_org="org-1", selected_plant="plant-1")
        assert False, "foreign evidence must be rejected"
    except PermissionError:
        pass
    assert SAFETY == {
        "read_only": True, "plc_write": False, "scada_control": False,
        "automatic_authorization": False, "automatic_execution": False,
        "human_decision_required": True, "causation_claim": False,
    }


def test_deduplication_is_deterministic():
    p = UnifiedIndustrialPlatform()
    now = datetime.now(timezone.utc)
    point = TelemetryPoint("o", "p", "PT-1", now, 10.0, sequence=7)
    a = p.ingest(point, selected_org="o", selected_plant="p")
    b = p.ingest(point, selected_org="o", selected_plant="p")
    assert a["accepted"] and not a["deduplicated"]
    assert b["accepted"] and b["deduplicated"]
