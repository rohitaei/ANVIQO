import anvi_chat_stability_v2 as chat
from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize


def test_engineering_headers_become_canonical_tag():
    for header in ("Instrument Tag", "Loop Tag", "PLC TAG", "TAG NAME"):
        row = normalize_record(
            {header: "PT-628", "description": "BF-2 pressure transmitter"},
            "INSTRUMENT",
        )
        assert row.tag == "PT-628", (header, row)
        assert normalize(row.tag) == "PT628"


def test_pci_resolver_resolves_bf2_record_without_pci_database():
    universal = [{
        "knowledge_id": "bf2-test-1",
        "organization_id": "org-bf2",
        "plant_id": "bf2",
        "record_type": "INSTRUMENT",
        "external_id": "bf2-test-1",
        "name": "BF-2 pressure transmitter",
        "area": "MBF",
        "service": "BF-2 pressure",
        "asset_type": "Instrument",
        "tag": "PT-628",
        "source": "BF2_TEST",
        "metadata": {"io_type": "AI", "plc_address": "PIW 628", "panel": "C2", "tb": "XA628"},
        "content": "PT-628 BF-2 pressure transmitter",
    }]
    adapted = [{
        "tag": r["tag"],
        "fox_plc_tag": "",
        "description": r["name"],
        "io_type": r["metadata"]["io_type"],
        "plc_address": r["metadata"]["plc_address"],
        "panel": r["metadata"]["panel"],
        "tb_name": r["metadata"]["tb"],
        "tb_no": "",
        "jb_name": "",
        "jb_no": "",
        "source_sheet": r["source"],
        "_universal_row": r,
    } for r in universal]

    for query in ("PT-628", "PT_628", "PT628"):
        resolved, match = resolve(query, adapted)
        assert resolved, (query, match)
        assert resolved[0]["_universal_row"]["tag"] == "PT-628"


def test_chat_pci_adapter_uses_tenant_rows_and_pci_resolver(monkeypatch):
    rows = [{
        "knowledge_id": "bf2-test-1",
        "organization_id": "org-bf2",
        "plant_id": "bf2",
        "record_type": "INSTRUMENT",
        "external_id": "bf2-test-1",
        "name": "BF-2 pressure transmitter",
        "area": "MBF",
        "service": "BF-2 pressure",
        "asset_type": "Instrument",
        "tag": "PT-628",
        "source": "BF2_TEST",
        "metadata": {"io_type": "AI", "plc_address": "PIW 628", "panel": "C2", "tb": "XA628"},
        "content": "PT-628 BF-2 pressure transmitter",
    }]

    class Store:
        def _placeholder(self):
            return "%"

    monkeypatch.setattr(chat, "_store", lambda: Store())
    monkeypatch.setattr(chat, "_execute", lambda sql, params: rows)

    result = chat._pci_resolve_rows("bf2", "org-bf2", "PT-628")
    assert result and result[0]["plant_id"] == "bf2"
    assert result[0]["tag"] == "PT-628"
