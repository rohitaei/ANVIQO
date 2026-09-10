import field_report_persistent_bridge as bridge


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
