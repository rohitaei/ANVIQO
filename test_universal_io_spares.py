import json
import sqlite3
from contextlib import contextmanager

import pytest

import anvi_tenant_chat_boundary as boundary
import pci_spares


def _row(tag="", external_id="", metadata=None, plant_id="plant-a"):
    return {
        "knowledge_id": "k1",
        "organization_id": "org-a",
        "plant_id": plant_id,
        "document_id": "doc-1",
        "record_type": "instrument",
        "external_id": external_id,
        "name": "Test point",
        "area": "TEST",
        "service": "Test service",
        "asset_type": "instrument",
        "tag": tag,
        "parent_id": "",
        "source": "test.xlsx",
        "metadata": metadata or {},
        "content": "",
    }


@pytest.mark.parametrize("tag", [
    "PT-303", "TT_101", "FT 202", "LT-303",
    "AI-401", "AO_402", "DI-501", "DO 502",
    "XV-601", "SOV_602", "ZSO-603", "MCV 604",
])
def test_universal_engineering_tag_detection(tag):
    assert boundary._candidate_tag("Tell me about " + tag) == boundary._normalize(tag)


def test_exact_answer_can_resolve_external_id_and_metadata_alias():
    plant = {"plant_id": "plant-a", "name": "Plant A"}
    row = _row(tag="", external_id="PT_303", metadata={"tag_no": "PT-303", "plc_address": "PIW 260"})
    result = boundary._tenant_answer("Tell me about PT303", [row], plant)
    assert result["blocked"] is False
    assert result["plant_id"] == "plant-a"
    assert "PIW 260" in result["answer"]


def test_rows_are_portable_and_strictly_tenant_scoped():
    class FakeStore:
        def _placeholder(self):
            return "?"

        @contextmanager
        def _connect(self):
            conn = sqlite3.connect(":memory:")
            try:
                conn.execute("""
                    CREATE TABLE anviqo_plant_knowledge (
                        knowledge_id TEXT, organization_id TEXT, plant_id TEXT,
                        document_id TEXT, record_type TEXT, external_id TEXT,
                        name TEXT, area TEXT, service TEXT, asset_type TEXT,
                        tag TEXT, parent_id TEXT, source TEXT, metadata TEXT,
                        content TEXT, created_at TEXT
                    )
                """)
                conn.executemany(
                    "INSERT INTO anviqo_plant_knowledge VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [
                        ("a", "org-a", "plant-a", "d", "instrument", "PT_303", "A", "A", "", "instrument", "PT_303", "", "a.xlsx", json.dumps({"tag_no": "PT-303"}), "", "1"),
                        ("b", "org-b", "plant-b", "d", "instrument", "PT303", "B", "B", "", "instrument", "PT303", "", "b.xlsx", json.dumps({"tag_no": "PT303"}), "", "1"),
                    ],
                )
                conn.commit()
                yield conn
            finally:
                conn.close()

    old = boundary._tenant_store
    boundary._tenant_store = lambda: FakeStore()
    try:
        rows = boundary._rows("plant-a", tag="PT-303")
        assert len(rows) == 1
        assert rows[0]["plant_id"] == "plant-a"
        assert rows[0]["tag"] == "PT_303"
    finally:
        boundary._tenant_store = old


def test_spare_exact_tag_supports_all_io_identifier_families(monkeypatch):
    spare = {
        "sheet": "Sheet1",
        "row": 2,
        "tag": "AI-401",
        "instrument": "Analog input spare",
        "description": "AI module",
        "specification": "test",
        "location": "Store",
        "qty_available": 2,
        "qty_required": 1,
        "spare_to_indent_recorded": 0,
        "spare_to_indent": 0,
        "status": "SUFFICIENT STOCK",
        "raw": {},
    }
    monkeypatch.setattr(pci_spares, "load_spares", lambda: [spare])
    assert pci_spares._extract_tag("How many spares of AI_401?") == "AI_401"
    assert pci_spares._norm("AI_401") == pci_spares._norm("AI-401")


def test_safety_boundary_remains_read_only():
    assert boundary.SAFETY["plc_write"] is False
    assert boundary.SAFETY["scada_control"] is False
    assert boundary.SAFETY["human_decision_required"] is True
