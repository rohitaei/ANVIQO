from anvi_inventory_intent import classify_spare_family_query


def test_family_level_pressure_spares_are_recognized():
    assert classify_spare_family_query("Spares of PT") == "PT"
    assert classify_spare_family_query("Zero stock of PT") == "PT"
    assert classify_spare_family_query("Show pressure transmitter inventory") == "PT"


def test_exact_tag_questions_are_left_for_exact_tag_resolver():
    assert classify_spare_family_query("Show spares for PT-303") is None


def test_multiple_equipment_families_are_supported():
    assert classify_spare_family_query("Available FT spares") == "FT"
    assert classify_spare_family_query("Shortage of solenoid valve spares") == "SOV"
    assert classify_spare_family_query("Show load cell inventory") == "LOAD CELL"


def test_non_inventory_equipment_questions_are_not_misrouted():
    assert classify_spare_family_query("What is PT-303?") is None
    assert classify_spare_family_query("Show PT-303 pressure trend") is None



def test_pt_family_query_returns_only_pt_sheet_records():
    from pci_spares import answer_spare_query

    result = answer_spare_query("Spares of PT")
    assert result is not None
    assert result["domain"] == "critical_spares"
    assert result["count"] > 0
    assert all(row.get("sheet") == "PT" for row in result["records"])


def test_zero_stock_pt_query_uses_the_same_authoritative_workbook():
    from pci_spares import answer_spare_query

    result = answer_spare_query("Zero stock of PT")
    assert result is not None
    assert result["domain"] == "critical_spares"
    assert all(row.get("sheet") == "PT" for row in result["records"])
    assert all(row.get("status") == "ZERO STOCK" for row in result["records"])
