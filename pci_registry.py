"""
ANVIQO PCI MASTER REGISTRY
===========================
Read-only retrieval layer over the verified PCI I/O database.

SOURCE OF TRUTH:
    database/pci/pci_instrument_database.json

Rules:
- Never modify the source database.
- Never invent missing fields.
- No PLC/SCADA writes.
- No duplicate V5 reasoning.
- Designed to support natural-language ANVI retrieval.
"""

import json
import os
import re
from collections import Counter

PCI_PATH = os.path.join(
    os.path.dirname(__file__),
    "database",
    "pci",
    "pci_instrument_database.json",
)


def load_records():
    with open(PCI_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])

    if not isinstance(records, list):
        raise ValueError("PCI database records is not a list")

    return records


def _text(value):
    return str(value or "").strip()


def _contains(value, query):
    return query.lower() in _text(value).lower()


def find_tag(tag):
    """Exact tag lookup."""
    target = _text(tag).upper()

    for record in load_records():
        if _text(record.get("tag")).upper() == target:
            return record

    return None


def search(
    query=None,
    area=None,
    io_type=None,
    description=None,
    process_role=None,
    panel=None,
    tb_name=None,
    criticality=None,
    limit=100,
):
    """
    Structured search across the real PCI records.
    Empty fields are ignored.
    """

    records = load_records()

    q = _text(query).lower()
    area_q = _text(area).lower()
    io_q = _text(io_type).upper()
    desc_q = _text(description).lower()
    role_q = _text(process_role).lower()
    panel_q = _text(panel).lower()
    tb_q = _text(tb_name).lower()
    critical_q = _text(criticality).upper()

    results = []

    for record in records:

        blob = " ".join(
            _text(record.get(k))
            for k in [
                "tag",
                "fox_plc_tag",
                "description",
                "area",
                "plc_address",
                "panel",
                "io_type",
                "tb_name",
                "tb_no",
                "field_elec",
                "criticality",
                "process_role",
            ]
        ).lower()

        if q and q not in blob:
            continue

        if area_q and area_q not in _text(
            record.get("area")
        ).lower():
            continue

        if io_q and _text(
            record.get("io_type")
        ).upper() != io_q:
            continue

        if desc_q and desc_q not in _text(
            record.get("description")
        ).lower():
            continue

        if role_q and role_q not in _text(
            record.get("process_role")
        ).lower():
            continue

        if panel_q and panel_q != _text(
            record.get("panel")
        ).lower():
            continue

        if tb_q and tb_q not in _text(
            record.get("tb_name")
        ).lower():
            continue

        if critical_q and _text(
            record.get("criticality")
        ).upper() != critical_q:
            continue

        results.append(record)

        if len(results) >= limit:
            break

    return results


def semantic_search_pci(
    query=None,
    area=None,
    io_type=None,
    panel=None,
    tb_name=None,
    criticality=None,
    kind=None,
    limit=1064,
):
    """
    Deterministic natural-language-friendly PCI search.

    This is a retrieval layer over the verified 1,064-record registry.
    It does not invent records and does not perform PLC/SCADA writes.
    """

    records = load_records()

    q = _text(query).strip().lower()
    area_q = _text(area).strip().lower()
    io_q = _text(io_type).strip().upper()
    panel_q = _text(panel).strip().lower()
    tb_q = _text(tb_name).strip().lower()
    critical_q = _text(criticality).strip().upper()
    kind_q = _text(kind).strip().lower()

    results = []

    for r in records:
        tag = _text(r.get("tag"))
        desc = _text(r.get("description"))
        role = _text(r.get("process_role"))
        area_v = _text(r.get("area"))
        io_v = _text(r.get("io_type"))
        panel_v = _text(r.get("panel"))
        tb_v = _text(r.get("tb_name"))
        critical_v = _text(r.get("criticality"))

        blob = " ".join([
            tag,
            desc,
            role,
            area_v,
            io_v,
            _text(r.get("plc_address")),
            panel_v,
            tb_v,
            _text(r.get("tb_no")),
            _text(r.get("field_elec")),
        ]).lower()

        if q and q not in blob:
            continue

        if area_q and area_q not in area_v.lower():
            continue

        # Exact I/O-type matching.
        if io_q:
            if io_v.upper() != io_q:
                continue

        if panel_q and panel_v.lower() != panel_q:
            continue

        if tb_q and tb_q not in tb_v.lower():
            continue

        if critical_q and critical_v.upper() != critical_q:
            continue

        # Semantic equipment/instrument type matching.
        if kind_q:
            if kind_q == "pressure_transmitter":
                # PT tags are authoritative when the tag starts with PT.
                # Descriptions/process roles provide a secondary signal.
                if not (
                    tag.upper().startswith("PT_")
                    or tag.upper().startswith("PT-")
                    or "pressure" in desc.lower()
                    or "pressure" in role.lower()
                ):
                    continue

            elif kind_q == "control_valve":
                if not any(
                    x in tag.upper()
                    for x in ("CV_", "CV-", "PCV_", "PCV-", "FCV_", "FCV-",
                              "TCV_", "TCV-", "LCV_", "LCV-", "XV_", "XV-",
                              "FV_", "FV-", "PV_", "PV-", "LV_", "LV-")
                ) and "control valve" not in blob:
                    continue

            elif kind_q == "valve":
                if not any(
                    x in tag.upper()
                    for x in ("CV_", "CV-", "PCV_", "PCV-", "FCV_", "FCV-",
                              "TCV_", "TCV-", "LCV_", "LCV-", "XV_", "XV-",
                              "FV_", "FV-", "PV_", "PV-", "LV_", "LV-")
                ) and "valve" not in blob:
                    continue

        results.append(r)

        if len(results) >= limit:
            break

    return results


def search_panel(panel, limit=1064):
    return semantic_search_pci(panel=panel, limit=limit)


def search_tb(tb_name, limit=1064):
    return semantic_search_pci(tb_name=tb_name, limit=limit)


def search_pressure_transmitters(limit=100):
    return semantic_search_pci(kind="pressure_transmitter", limit=limit)


def search_control_valves(limit=100):
    return semantic_search_pci(kind="control_valve", limit=limit)



def search_pressure_transmitters(limit=100):
    return semantic_search_pci(kind="pressure_transmitter", limit=limit)


def search_area(area, limit=100):
    return search(area=area, limit=limit)


def search_io(io_type, limit=100):
    return search(io_type=io_type, limit=limit)


def search_critical(limit=100):
    return [
        r for r in load_records()
        if _text(r.get("criticality")).upper() == "HIGH"
    ][:limit]


def summary():
    records = load_records()

    return {
        "source": "database/pci/pci_instrument_database.json",
        "record_count": len(records),
        "areas": dict(
            Counter(
                _text(r.get("area")) or "UNKNOWN"
                for r in records
            )
        ),
        "io_types": dict(
            Counter(
                _text(r.get("io_type")) or "UNKNOWN"
                for r in records
            )
        ),
        "panels": dict(
            Counter(
                _text(r.get("panel")) or "UNKNOWN"
                for r in records
            )
        ),
    }


def compact(record):
    """Safe presentation format; preserves source values."""
    return {
        "tag": record.get("tag", ""),
        "description": record.get("description", ""),
        "area": record.get("area", ""),
        "io_type": record.get("io_type", ""),
        "plc_address": record.get("plc_address", ""),
        "fox_plc_tag": record.get("fox_plc_tag", ""),
        "panel": record.get("panel", ""),
        "tb_name": record.get("tb_name", ""),
        "tb_no": record.get("tb_no", ""),
        "field_elec": record.get("field_elec", ""),
        "criticality": record.get("criticality", ""),
        "process_role": record.get("process_role", ""),
        "source_sheet": record.get("source_sheet", ""),
    }


def run_test():
    records = load_records()

    print("=" * 72)
    print("ANVIQO PCI MASTER REGISTRY TEST")
    print("=" * 72)

    print("\nSOURCE")
    print("Path       :", PCI_PATH)
    print("Records    :", len(records))

    assert len(records) == 1064, (
        f"Expected 1064 PCI records, found {len(records)}"
    )

    print("\nTEST 1 — EXACT TAG")
    lp = find_tag("LP_1_Healthy")
    assert lp is not None
    print(json.dumps(compact(lp), indent=2, ensure_ascii=False))

    print("\nTEST 2 — VRM / MILL")
    vrm = search_area("VRM / MILL", limit=10)
    print("Returned:", len(vrm), "sample records")

    print("\nTEST 3 — PRESSURE TRANSMITTER")
    pt = search_pressure_transmitters(limit=10)
    print("Returned:", len(pt), "sample records")
    for r in pt[:5]:
        print(
            r.get("tag"),
            "|",
            r.get("description"),
            "|",
            r.get("area"),
        )

    print("\nTEST 4 — DI")
    di = search_io("DI", limit=10)
    print("Returned:", len(di), "sample records")

    print("\nTEST 5 — HIGH CRITICALITY")
    critical = search_critical(limit=10)
    print("Returned:", len(critical), "sample records")

    print("\nTEST 6 — SUMMARY")
    s = summary()
    print("Areas    :", len(s["areas"]))
    print("I/O types:", s["io_types"])
    print("Panels   :", s["panels"])

    print("\n" + "=" * 72)
    print("PCI MASTER REGISTRY : PASS")
    print("SOURCE DATABASE      : PRESERVED")
    print("RECORD COUNT         : 1064")
    print("READ ONLY            : TRUE")
    print("V5 MODIFIED          : FALSE")
    print("=" * 72)


if __name__ == "__main__":
    run_test()
