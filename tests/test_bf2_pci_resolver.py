from universal_onboarding import normalize_record
from pci_universal_resolver import resolve, normalize

def main():
    row = normalize_record({"Instrument Tag":"PT-628","description":"BF-2 pressure transmitter"}, "INSTRUMENT")
    if row.tag != "PT-628": raise AssertionError(("canonical_tag", row.tag))
    if normalize(row.tag) != "PT628": raise AssertionError(("normalized_tag", normalize(row.tag)))

    record = {
        "tag":"PT-628","fox_plc_tag":"","description":"BF-2 pressure transmitter",
        "io_type":"AI","plc_address":"PIW 628","panel":"C2","tb_name":"XA628",
        "tb_no":"","jb_name":"","jb_no":"","source_sheet":"BF2_TEST"
    }
    record["_universal_row"]={"plant_id":"bf2","tag":"PT-628"}
    for q in ("PT-628","PT_628","PT628"):
        rows, match = resolve(q, [record])
        if not rows: raise AssertionError(("resolver_empty", q, match))
        if rows[0]["_universal_row"]["tag"] != "PT-628":
            raise AssertionError(("wrong_row", q, rows[0]))
    print("BF-2 PCI resolver predeploy check: PASS")

if __name__ == "__main__":
    main()
