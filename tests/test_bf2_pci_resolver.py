from dataclasses import asdict
from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize
from anvi_chat_stability_v2 import _field

def main():
    row = normalize_record(
        {"Instrument Tag": "PT-628", "description": "BF-2 pressure transmitter", "I/O TYPE": "AI", "PLC ADDRESS": "PIW 628", "PANEL": "C2", "TB NAME": "XA628", "TB NO": "14", "JB NAME": "JB-62", "JB NO": "5", "RANGE": "0-10 bar", "UNIT": "bar", "MODEL": "TX-100", "CRITICALITY": "CRITICAL"},
        "INSTRUMENT",
    )
    normalized = asdict(row)
    assert normalized["tag"] == "PT-628", ("canonical_tag", normalized)
    rendered = _field({"tag":"PT-628","external_id":"bf2-test","name":"Pressure transmitter","area":"BF-2","source":"BF2_TEST","metadata":normalized["metadata"]})
    for expected in ("I/O: AI","PLC: PIW 628","Panel: C2","TB: XA628","TB No: 14","JB: JB-62","JB No: 5","Range: 0-10 bar","Unit: bar","Model: TX-100","Criticality: CRITICAL"):
        assert expected in rendered, ("missing_engineering_field", expected, rendered)
    assert normalize(normalized["tag"]) == "PT628", ("normalized_tag", normalized)

    record = {
        "tag": normalized["tag"],
        "fox_plc_tag": normalized["metadata"].get("plc_tag", ""),
        "description": normalized["name"],
        "io_type": normalized["metadata"].get("io_type", "AI"),
        "plc_address": normalized["metadata"].get("plc_address", "PIW 628"),
        "panel": normalized["metadata"].get("panel", "C2"),
        "tb_name": normalized["metadata"].get("tb", "XA628"),
        "tb_no": normalized["metadata"].get("tb_no", ""),
        "jb_name": normalized["metadata"].get("jb", ""),
        "jb_no": normalized["metadata"].get("jb_no", ""),
        "source_sheet": "BF2_TEST",
        "_universal_row": normalized,
    }

    for query in ("PT-628", "PT_628", "PT628"):
        rows, match = resolve(query, [record])
        assert rows, ("resolver_empty", query, match, record)
        assert any(r.get("_universal_row", {}).get("tag") == "PT-628" for r in rows), (
            "wrong_row", query, match, rows
        )

    print("BF-2 PCI resolver predeploy check: PASS")

if __name__ == "__main__":
    main()
