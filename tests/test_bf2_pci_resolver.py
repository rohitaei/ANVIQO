import ast
from pathlib import Path

from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize


def main():
    # 1. Engineering-sheet headers must canonicalize into the same tag.
    for header in ("Instrument Tag", "Loop Tag", "PLC TAG", "TAG NAME"):
        row = normalize_record({header: "PT-628", "description": "BF-2 pressure transmitter"}, "INSTRUMENT")
        assert row.tag == "PT-628", (header, row.tag)
        assert normalize(row.tag) == "PT628"

    # 2. The proven PCI resolver must resolve BF-2-supplied data,
    #    without loading the PCI JSON database.
    bf2 = {
        "tag": "PT-628",
        "fox_plc_tag": "",
        "description": "BF-2 pressure transmitter",
        "io_type": "AI",
        "plc_address": "PIW 628",
        "panel": "C2",
        "tb_name": "XA628",
        "tb_no": "",
        "jb_name": "",
        "jb_no": "",
        "source_sheet": "BF2_TEST",
    }
    bf2["_universal_row"] = {"plant_id": "bf2", "tag": "PT-628"}

    for query in ("PT-628", "PT_628", "PT628"):
        resolved, match = resolve(query, [bf2])
        assert resolved, (query, match)
        assert resolved[0]["_universal_row"]["tag"] == "PT-628"

    # 3. Verify the production adapter actually imports the proven resolver
    #    and contains the tenant-scoped BF-2 adapter function.
    source = Path("anvi_chat_stability_v2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    text = source.replace(" ", "").replace("\n", "")
    assert "frompci_universal_resolverimportresolve" in text
    assert "def_pci_resolve_rows(" in text
    assert "plant_id={p}" in source
    assert "organization_id={p}" in source
    assert "LIMIT5000" in text

    print("BF-2 PCI resolver predeploy check: PASS")

if __name__ == "__main__":
    main()
