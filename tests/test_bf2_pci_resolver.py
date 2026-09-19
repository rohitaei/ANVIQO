from dataclasses import asdict
from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize

def main():
    row = normalize_record(
        {"Instrument Tag": "PT-628", "description": "BF-2 pressure transmitter"},
        "INSTRUMENT",
    )
    normalized = asdict(row)
    assert normalized["tag"] == "PT-628", ("canonical_tag", normalized)
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
