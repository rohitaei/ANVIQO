from universal_plant_data import enrich_workbook_records

def _base_records(status="DEMO_ONLY", mode="SIMULATION", unit="bar"):
    rows=[{
        "record_type":"INSTRUMENT","tag":"PT_303","range_min":0,"range_max":10,
        "range_unit":unit,"configuration_status":status,"data_mode":mode,
        "approver":"ENG-1" if status=="APPROVED" else "",
        "approval_reference":"MOC-123" if status=="APPROVED" else "",
    }]
    for cls,direction,value in [
        ("WARNING","LOW",1),("WARNING","HIGH",9),
        ("CRITICAL","LOW",0),("CRITICAL","HIGH",10),
    ]:
        rows.append({
            "record_type":"ALARM_LIMIT","tag":"PT_303","alarm_class":cls,
            "direction":direction,"setpoint":value,"unit":unit,
            "configuration_status":status,
            "approver":"ENG-1" if status=="APPROVED" else "",
            "approval_reference":"MOC-123" if status=="APPROVED" else "",
        })
    return rows

def test_demo_only_profile_can_assess_simulation_but_is_not_engineering_approval():
    out=enrich_workbook_records(_base_records())
    cfg=out[0]["approved_engineering_limits"]
    assert cfg["approved"] is True
    assert cfg["approval_basis"]=="DEMO_PROFILE"
    assert cfg["warning_low"]==1
    assert cfg["critical_high"]==10

def test_demo_profile_cannot_be_used_for_non_simulation_data():
    out=enrich_workbook_records(_base_records(mode="LIVE"))
    assert "approved_engineering_limits" not in out[0]

def test_operational_profile_requires_approver_and_reference():
    out=enrich_workbook_records(_base_records(status="APPROVED"))
    assert out[0]["approved_engineering_limits"]["approval_basis"]=="ENGINEERING_APPROVED"
    bad=_base_records(status="APPROVED")
    bad[0]["approval_reference"]=""
    out=enrich_workbook_records(bad)
    assert "approved_engineering_limits" not in out[0]

def test_mismatched_alarm_units_block_configuration():
    rows=_base_records()
    rows[-1]["unit"]="kPa"
    out=enrich_workbook_records(rows)
    assert "approved_engineering_limits" not in out[0]

def test_digital_semantics_are_explicit_and_separate_from_analog_limits():
    rows=[{
        "record_type":"INSTRUMENT","tag":"PUMP_OK","io_type":"DI",
        "data_mode":"SIMULATION","configuration_status":"DEMO_ONLY",
    },{
        "record_type":"DIGITAL_SEMANTICS","tag":"PUMP_OK",
        "normal_states":"1","alarm_states":"0","configuration_status":"DEMO_ONLY",
    }]
    out=enrich_workbook_records(rows)
    assert out[0]["approved_signal_semantics"]["normal_states"]==[1]
    assert out[0]["approved_signal_semantics"]["alarm_states"]==[0]
