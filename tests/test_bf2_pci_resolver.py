import anvi_chat_stability_v2 as chat
from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize

def main():
    for header in ("Instrument Tag", "Loop Tag", "PLC TAG", "TAG NAME"):
        row = normalize_record({header: "PT-628", "description": "BF-2 pressure transmitter"}, "INSTRUMENT")
        assert row.tag == "PT-628", (header, row.tag)
        assert normalize(row.tag) == "PT628"

    row = {
        "knowledge_id":"bf2-test-1","organization_id":"org-bf2","plant_id":"bf2",
        "record_type":"INSTRUMENT","external_id":"bf2-test-1",
        "name":"BF-2 pressure transmitter","area":"MBF","service":"BF-2 pressure",
        "asset_type":"Instrument","tag":"PT-628","source":"BF2_TEST",
        "metadata":{"io_type":"AI","plc_address":"PIW 628","panel":"C2","tb":"XA628"},
        "content":"PT-628 BF-2 pressure transmitter",
    }
    adapted=[{
        "tag":row["tag"],"fox_plc_tag":"","description":row["name"],
        "io_type":row["metadata"]["io_type"],"plc_address":row["metadata"]["plc_address"],
        "panel":row["metadata"]["panel"],"tb_name":row["metadata"]["tb"],"tb_no":"",
        "jb_name":"","jb_no":"","source_sheet":row["source"],"_universal_row":row
    }]
    for q in ("PT-628","PT_628","PT628"):
        resolved, match = resolve(q, adapted)
        assert resolved and resolved[0]["_universal_row"]["tag"] == "PT-628", (q, match, resolved)

    class Store:
        def _placeholder(self): return "%"

    chat._store = lambda: Store()
    chat._execute = lambda sql, params: [row]
    result = chat._pci_resolve_rows("bf2","org-bf2","PT-628")
    assert result and result[0]["plant_id"] == "bf2" and result[0]["tag"] == "PT-628", result
    print("BF-2 PCI resolver predeploy check: PASS")

if __name__ == "__main__":
    main()
