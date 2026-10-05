from anvi_v2_month_soak_simulator import run_month_soak

def test_30_day_end_to_end_simulation():
    result=run_month_soak()
    assert result["status"]=="PASS"
    assert result["stats"]["days"]==30
    assert result["stats"]["telemetry_stored"]==result["stats"]["telemetry_attempted"]
    assert result["stats"]["duplicate_attempts"]>0
    assert result["stats"]["events"]>0
    assert result["stats"]["replay_windows"]==2
    assert result["stats"]["tenant_blocks"]==2
    assert result["stats"]["write_blocks"]==2
    assert result["stats"]["audit_records"]==2
    assert result["stats"]["reports"]==3
    assert result["stored_snapshot"]["plc_write"] is False
    assert result["stored_snapshot"]["scada_control"] is False
    assert result["pov"]["pov_ready"] is True
    assert result["pov"]["production_deploy"]=="REQUIRES_EXTERNAL_CERTIFICATION_AND_APPROVAL"
