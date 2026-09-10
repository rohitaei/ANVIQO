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
