from pathlib import Path

import pytest

import field_report_runtime as runtime
from anvi_field_report import parse_field_report


def _make_workbook(path: Path, tag="PT-303", qty=3):
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "PT"
    ws.append(["Instrument", "Qty avbl"])
    ws.append([tag, qty])
    wb.save(path)


def test_explicit_spare_use_is_parsed():
    report = parse_field_report(
        "PT-303 transmitter was replaced. One PT-303 spare used."
    )
    assert report["tag"] == "PT-303"
    assert report["spare_used"] in {"PT-303 x1", "PT-303 x1.0"}


def test_field_report_reduces_excel_once(tmp_path, monkeypatch):
    workbook = tmp_path / "critical_spares.xlsx"
    audit = tmp_path / "critical_spare_transactions.json"
    ledger = tmp_path / "field_report_spare_sync.json"
    _make_workbook(workbook, qty=3)

    import pci_spare_direct_excel
    monkeypatch.setattr(pci_spare_direct_excel, "XLSX", workbook)
    monkeypatch.setattr(pci_spare_direct_excel, "AUDIT", audit)
    monkeypatch.setattr(runtime, "LEDGER", ledger)

    parsed = parse_field_report(
        "PT-303 transmitter was replaced. One PT-303 spare used."
    )

    first = runtime.sync_field_report_spare(parsed, "PM-TEST-001")
    assert first["status"] == "APPLIED"
    assert first["inventory_changed"] is True
    assert first["before"] == 3
    assert first["after"] == 2

    second = runtime.sync_field_report_spare(parsed, "PM-TEST-001")
    assert second["status"] == "ALREADY_APPLIED"
    assert second["inventory_changed"] is False
    assert second["after"] == 2

    from pci_spare_direct_excel import get_spare_quantity
    assert get_spare_quantity("PT-303") == 2


def test_spare_mention_without_use_does_not_change_stock(tmp_path, monkeypatch):
    workbook = tmp_path / "critical_spares.xlsx"
    audit = tmp_path / "critical_spare_transactions.json"
    ledger = tmp_path / "field_report_spare_sync.json"
    _make_workbook(workbook, qty=3)

    import pci_spare_direct_excel
    monkeypatch.setattr(pci_spare_direct_excel, "XLSX", workbook)
    monkeypatch.setattr(pci_spare_direct_excel, "AUDIT", audit)
    monkeypatch.setattr(runtime, "LEDGER", ledger)

    parsed = parse_field_report(
        "PT-303 transmitter checked. PT-303 spare is available in store."
    )
    result = runtime.sync_field_report_spare(parsed, "PM-TEST-002")
    assert result["status"] == "NOT_APPLICABLE"
    assert result["inventory_changed"] is False


def test_negative_inventory_is_blocked(tmp_path, monkeypatch):
    workbook = tmp_path / "critical_spares.xlsx"
    audit = tmp_path / "critical_spare_transactions.json"
    ledger = tmp_path / "field_report_spare_sync.json"
    _make_workbook(workbook, qty=0)

    import pci_spare_direct_excel
    monkeypatch.setattr(pci_spare_direct_excel, "XLSX", workbook)
    monkeypatch.setattr(pci_spare_direct_excel, "AUDIT", audit)
    monkeypatch.setattr(runtime, "LEDGER", ledger)

    parsed = parse_field_report(
        "PT-303 transmitter was replaced. One PT-303 spare used."
    )
    with pytest.raises(ValueError, match="Only 0 available"):
        runtime.sync_field_report_spare(parsed, "PM-TEST-003")


def test_later_report_question_returns_persistent_field_evidence(monkeypatch):
    report = {
        "memory_id": "PM-TEST-004",
        "tag": "PT-303",
        "equipment": "PT-303",
        "source": "technician field report",
        "observation": "No indication",
        "finding": "Fuse blown",
        "maintenance_action": "Fuse replaced",
        "outcome": "Instrument returned to normal operation",
        "spare_used": "none reported",
        "verification_status": "PENDING_VERIFICATION",
    }

    import plant_memory
    monkeypatch.setattr(plant_memory, "search_all_memory", lambda **kwargs: [report])

    answer = runtime.answer_field_report_query("What happened to PT-303 last time?")
    assert answer is not None
    assert answer["memory_id"] == "PM-TEST-004"
    assert "Fuse replaced" in answer["answer"]
    assert answer["verification_status"] == "PENDING_VERIFICATION"
