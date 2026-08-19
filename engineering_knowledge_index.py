"""
ANVIQO ENGINEERING KNOWLEDGE INDEX
==================================

Purpose
-------
Build a unified, source-backed engineering knowledge index without
replacing the existing V5 intelligence or PCI registry.

Sources
-------
1. Existing PCI JSON
2. Existing PCI CSV
3. PCI PLC TOTAL IO.xlsx
4. PCI_INSTRUMENT_RANGE.xlsx
5. critical spares in pci.xlsx
6. MBF2 PCI cable schedule.xlsx
7. MBF2 PCI cable schedule (1).xlsx

Design rules
------------
- Read-only with respect to existing intelligence.
- No pandas/openpyxl dependency.
- Python standard library only.
- Preserve source values.
- Never invent engineering values.
- Normalize tags only for matching; preserve original values.
- Maintain source provenance.
- Build cross-domain relationships.
"""

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from collections import Counter, defaultdict
import csv
import json
import re
import hashlib
from datetime import datetime


DOWNLOAD = Path("/storage/emulated/0/Download")
PROJECT = Path(".")
OUT = PROJECT / "database" / "engineering" / "index"
OUT.mkdir(parents=True, exist_ok=True)

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


# ----------------------------------------------------------------------
# BASIC UTILITIES
# ----------------------------------------------------------------------

def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm(value):
    """
    Matching normalization only.
    Original engineering values are always preserved separately.
    """
    value = clean(value).upper()

    value = value.replace("–", "-").replace("—", "-")
    value = value.replace(" ", "")
    value = value.replace("/", "")
    value = value.replace("\\", "")
    value = value.replace("(", "")
    value = value.replace(")", "")

    return value


def norm_tag(value):
    value = clean(value).upper()

    if not value:
        return ""

    value = value.replace(" ", "")
    value = value.replace("–", "-")
    value = value.replace("—", "-")

    # Common engineering tag variations:
    # PT303 -> PT_303
    # PT-303 -> PT_303
    m = re.match(r"^([A-Z]+)[-_]?(\d+)(.*)$", value)

    if m:
        prefix = m.group(1)
        number = m.group(2)
        suffix = m.group(3)

        if suffix:
            return f"{prefix}_{number}_{suffix.lstrip('_-')}"

        return f"{prefix}_{number}"

    return value


def file_sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ----------------------------------------------------------------------
# XLSX READER
# ----------------------------------------------------------------------

def xlsx_sheets(path):

    with ZipFile(path) as z:

        workbook = ET.fromstring(
            z.read("xl/workbook.xml")
        )

        rels = ET.fromstring(
            z.read("xl/_rels/workbook.xml.rels")
        )

        rel_map = {}

        for rel in rels:
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")

            if target.startswith("/"):
                target = target[1:]

            if not target.startswith("xl/"):
                target = "xl/" + target

            rel_map[rid] = target

        result = []

        sheets = workbook.find("main:sheets", NS)

        if sheets is None:
            return result

        for sheet in sheets:

            name = sheet.attrib.get("name", "")

            rid = sheet.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )

            target = rel_map.get(rid)

            if target:
                result.append((name, target))

        return result


def xlsx_shared_strings(z):

    if "xl/sharedStrings.xml" not in z.namelist():
        return []

    root = ET.fromstring(
        z.read("xl/sharedStrings.xml")
    )

    values = []

    for si in root.findall("main:si", NS):

        parts = []

        for t in si.iter("{%s}t" % NS["main"]):
            parts.append(t.text or "")

        values.append(clean("".join(parts)))

    return values


def col_number(col):

    n = 0

    for ch in col:
        n = n * 26 + ord(ch) - 64

    return n


def read_xlsx_rows(path, sheet_target):

    with ZipFile(path) as z:

        shared = xlsx_shared_strings(z)

        root = ET.fromstring(
            z.read(sheet_target)
        )

        result = []

        sheet_data = root.find("main:sheetData", NS)

        if sheet_data is None:
            return result

        for row in sheet_data.findall("main:row", NS):

            values = {}

            for cell in row.findall("main:c", NS):

                ref = cell.attrib.get("r", "")

                m = re.match(r"([A-Z]+)", ref)

                if not m:
                    continue

                col = m.group(1)

                typ = cell.attrib.get("t")

                value_node = cell.find("main:v", NS)

                if typ == "inlineStr":

                    text_parts = []

                    for t in cell.iter(
                        "{%s}t" % NS["main"]
                    ):
                        text_parts.append(t.text or "")

                    value = "".join(text_parts)

                elif value_node is None:

                    value = ""

                else:

                    value = value_node.text or ""

                    if typ == "s":

                        try:
                            value = shared[int(value)]
                        except Exception:
                            pass

                    elif typ == "b":

                        value = (
                            "TRUE"
                            if value == "1"
                            else "FALSE"
                        )

                values[col] = clean(value)

            if values:
                result.append(values)

    return result


def matrix(rows):

    if not rows:
        return []

    columns = set()

    for row in rows:
        columns.update(row.keys())

    columns = sorted(
        columns,
        key=col_number
    )

    return [
        [row.get(col, "") for col in columns]
        for row in rows
    ]


def read_workbook(path):

    workbook = []

    for sheet_name, target in xlsx_sheets(path):

        rows = read_xlsx_rows(
            path,
            target
        )

        workbook.append({
            "sheet": sheet_name,
            "target": target,
            "rows": matrix(rows),
        })

    return workbook


# ----------------------------------------------------------------------
# HEADER DETECTION
# ----------------------------------------------------------------------

def normalize_header(value):

    value = clean(value).lower()

    value = value.replace("\n", " ")
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def find_header(rows):

    best_index = None
    best_score = -1

    expected = [
        "tag",
        "instrument",
        "description",
        "range",
        "unit",
        "plc",
        "panel",
        "tb",
        "terminal",
        "spare",
        "part",
        "cable",
        "core",
        "from",
        "to",
    ]

    for i, row in enumerate(rows[:30]):

        headers = [
            normalize_header(x)
            for x in row
        ]

        score = 0

        for h in headers:

            for token in expected:

                if token in h:
                    score += 1
                    break

        if score > best_score:

            best_score = score
            best_index = i

    if best_index is None:
        return [], rows

    return (
        [
            normalize_header(x) or f"column_{j+1}"
            for j, x in enumerate(rows[best_index])
        ],
        rows[best_index + 1:]
    )


def dict_rows(rows):

    headers, data = find_header(rows)

    if not headers:
        return []

    result = []

    for row in data:

        record = {}

        for i, header in enumerate(headers):

            if i < len(row):
                record[header] = clean(row[i])
            else:
                record[header] = ""

        if any(record.values()):
            result.append(record)

    return result


# ----------------------------------------------------------------------
# FIELD CLASSIFICATION
# ----------------------------------------------------------------------

def first_field(record, keywords):

    for key, value in record.items():

        key_n = normalize_header(key)

        for keyword in keywords:

            if keyword in key_n and clean(value):
                return clean(value)

    return ""


def record_tag(record):

    direct = first_field(
        record,
        [
            "tag",
            "instrument_tag",
            "device_tag",
            "loop_tag",
            "io_tag",
        ]
    )

    if direct:
        return direct

    # Search values conservatively for engineering tags.
    for value in record.values():

        value = clean(value)

        if re.match(
            r"^[A-Za-z]{1,12}[-_]?\d{1,5}([A-Za-z0-9_-]*)$",
            value
        ):
            return value

    return ""


def extract_range(record):

    return first_field(
        record,
        [
            "range",
            "instrument_range",
            "measurement_range",
            "calibration_range",
            "span",
            "range_value",
        ]
    )


def extract_unit(record):

    return first_field(
        record,
        [
            "unit",
            "units",
            "engineering_unit",
            "engg_unit",
        ]
    )


def extract_description(record):

    return first_field(
        record,
        [
            "description",
            "instrument_description",
            "item_description",
            "details",
            "service",
        ]
    )


def extract_part(record):

    return first_field(
        record,
        [
            "part_no",
            "part_number",
            "material_code",
            "item_code",
            "stock_code",
            "spare_code",
        ]
    )


def extract_quantity(record):

    return first_field(
        record,
        [
            "qty",
            "quantity",
            "stock",
            "available",
            "balance",
        ]
    )


def extract_cable(record):

    return first_field(
        record,
        [
            "cable",
            "cable_no",
            "cable_number",
            "cable_tag",
        ]
    )


def extract_terminal(record):

    return first_field(
        record,
        [
            "tb",
            "tb_name",
            "terminal",
            "terminal_block",
            "terminal_no",
        ]
    )


# ----------------------------------------------------------------------
# PCI MASTER LOAD
# ----------------------------------------------------------------------

def load_pci_json():

    candidates = [
        PROJECT / "database/pci/pci_instrument_database.json",
        DOWNLOAD / "pci_instrument_database.json",
    ]

    for path in candidates:

        if not path.exists():
            continue

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(data, list):
                return data, str(path)

        except Exception:
            pass

    return [], ""


def load_pci_csv():

    candidates = [
        DOWNLOAD / "pci_instrument_database.csv",
        DOWNLOAD / "pci_instrument_database-1.csv",
    ]

    for path in candidates:

        if not path.exists():
            continue

        records = []

        try:

            with path.open(
                "r",
                encoding="utf-8-sig",
                errors="replace",
                newline=""
            ) as f:

                reader = csv.DictReader(f)

                for row in reader:
                    records.append({
                        clean(k): clean(v)
                        for k, v in row.items()
                    })

            return records, str(path)

        except Exception:
            pass

    return [], ""


# ----------------------------------------------------------------------
# SOURCE INGESTION
# ----------------------------------------------------------------------

def ingest_xlsx(path, source_type):

    if not path.exists():
        return []

    records = []

    try:

        for workbook_sheet in read_workbook(path):

            sheet = workbook_sheet["sheet"]
            rows = workbook_sheet["rows"]

            for record in dict_rows(rows):

                record["_source_file"] = path.name
                record["_source_sheet"] = sheet
                record["_source_type"] = source_type

                records.append(record)

    except Exception as e:

        print(
            "WARNING: Could not read",
            path,
            repr(e)
        )

    return records


# ----------------------------------------------------------------------
# MASTER INDEX
# ----------------------------------------------------------------------

def main():

    print("=" * 90)
    print("ANVIQO ENGINEERING KNOWLEDGE INDEX BUILD")
    print("=" * 90)

    build_time = datetime.now().isoformat()

    # --------------------------------------------------------------
    # PCI
    # --------------------------------------------------------------

    pci_json, pci_json_source = load_pci_json()

    pci_csv, pci_csv_source = load_pci_csv()

    if len(pci_json) >= len(pci_csv):

        pci_records = pci_json
        pci_source = pci_json_source

    else:

        pci_records = pci_csv
        pci_source = pci_csv_source

    print("PCI MASTER RECORDS:", len(pci_records))
    print("PCI SOURCE:", pci_source)

    instruments = {}

    for record in pci_records:

        tag = clean(record.get("tag", ""))

        if not tag:
            continue

        key = norm_tag(tag)

        if key not in instruments:

            instruments[key] = {
                "tag": tag,
                "normalized_tag": key,
                "description": clean(
                    record.get("description", "")
                ),
                "area": clean(
                    record.get("area", "")
                ),
                "io_type": clean(
                    record.get("io_type", "")
                ),
                "plc_address": clean(
                    record.get("plc_address", "")
                ),
                "fox_plc_tag": clean(
                    record.get("fox_plc_tag", "")
                ),
                "panel": clean(
                    record.get("panel", "")
                ),
                "tb_name": clean(
                    record.get("tb_name", "")
                ),
                "tb_no": clean(
                    record.get("tb_no", "")
                ),
                "field_elec": clean(
                    record.get("field_elec", "")
                ),
                "criticality": clean(
                    record.get("criticality", "")
                ),
                "process_role": clean(
                    record.get("process_role", "")
                ),
                "sources": [
                    "pci_instrument_database"
                ],
                "range": [],
                "spares": [],
                "cables": [],
                "relationships": [],
            }

    # --------------------------------------------------------------
    # RANGE
    # --------------------------------------------------------------

    range_path = DOWNLOAD / "PCI_INSTRUMENT_RANGE.xlsx"

    range_records = ingest_xlsx(
        range_path,
        "instrument_range"
    )

    print("RANGE SOURCE RECORDS:", len(range_records))

    range_links = 0

    for record in range_records:

        tag = record_tag(record)

        if not tag:
            continue

        key = norm_tag(tag)

        if key not in instruments:
            continue

        item = instruments[key]

        range_value = extract_range(record)
        unit = extract_unit(record)
        description = extract_description(record)

        if range_value or unit:

            item["range"].append({
                "range": range_value,
                "unit": unit,
                "description": description,
                "source_file": record["_source_file"],
                "source_sheet": record["_source_sheet"],
            })

            if "instrument_range" not in item["sources"]:
                item["sources"].append(
                    "instrument_range"
                )

            range_links += 1

    # --------------------------------------------------------------
    # SPARES
    # --------------------------------------------------------------

    spare_path = DOWNLOAD / "critical spares in pci.xlsx"

    spare_records = ingest_xlsx(
        spare_path,
        "critical_spare"
    )

    print("SPARE SOURCE RECORDS:", len(spare_records))

    spare_links = 0

    for record in spare_records:

        tag = record_tag(record)

        # Some spare sheets may not have tags.
        # Preserve them in the orphan spare inventory.
        if not tag:
            continue

        key = norm_tag(tag)

        if key not in instruments:
            continue

        item = instruments[key]

        spare = {
            "description": extract_description(record),
            "part_number": extract_part(record),
            "quantity": extract_quantity(record),
            "raw": record,
            "source_file": record["_source_file"],
            "source_sheet": record["_source_sheet"],
        }

        item["spares"].append(spare)

        if "critical_spares" not in item["sources"]:
            item["sources"].append(
                "critical_spares"
            )

        spare_links += 1

    # --------------------------------------------------------------
    # CABLE SCHEDULES
    # --------------------------------------------------------------

    cable_paths = [
        DOWNLOAD / "MBF2  PCI  cable schedule .xlsx",
        DOWNLOAD / "MBF2  PCI  cable schedule  (1).xlsx",
    ]

    cable_records = []

    for path in cable_paths:

        cable_records.extend(
            ingest_xlsx(
                path,
                "cable_schedule"
            )
        )

    print("CABLE SOURCE RECORDS:", len(cable_records))

    cable_links = 0

    for record in cable_records:

        possible_tags = []

        for value in record.values():

            value = clean(value)

            if not value:
                continue

            for match in re.findall(
                r"\b[A-Za-z]{1,12}[-_]?\d{1,5}(?:[-_][A-Za-z0-9]+)*\b",
                value
            ):

                possible_tags.append(match)

        linked = set()

        for tag in possible_tags:

            key = norm_tag(tag)

            if key in instruments:
                linked.add(key)

        for key in linked:

            instruments[key]["cables"].append({
                "cable": extract_cable(record),
                "terminal": extract_terminal(record),
                "raw": record,
                "source_file": record["_source_file"],
                "source_sheet": record["_source_sheet"],
            })

            if "cable_schedule" not in instruments[key]["sources"]:
                instruments[key]["sources"].append(
                    "cable_schedule"
                )

            cable_links += 1

    # --------------------------------------------------------------
    # PLC TOTAL IO CROSS-CHECK
    # --------------------------------------------------------------

    plc_path = DOWNLOAD / "PCI PLC TOTAL IO.xlsx"

    plc_records = ingest_xlsx(
        plc_path,
        "plc_total_io"
    )

    print("PLC SOURCE RECORDS:", len(plc_records))

    plc_links = 0

    for record in plc_records:

        tag = record_tag(record)

        if not tag:
            continue

        key = norm_tag(tag)

        if key not in instruments:
            continue

        item = instruments[key]

        # Do not overwrite the master PCI values.
        # Only record the PLC source as corroboration.
        if "plc_total_io" not in item["sources"]:
            item["sources"].append(
                "plc_total_io"
            )

        plc_links += 1

    # --------------------------------------------------------------
    # RELATIONSHIP INDEX
    # --------------------------------------------------------------

    by_area = defaultdict(list)
    by_panel = defaultdict(list)
    by_tb = defaultdict(list)
    by_io = defaultdict(list)
    by_prefix = Counter()

    for key, item in instruments.items():

        if item["area"]:
            by_area[
                item["area"]
            ].append(item["tag"])

        if item["panel"]:
            by_panel[
                item["panel"]
            ].append(item["tag"])

        if item["tb_name"]:
            by_tb[
                item["tb_name"]
            ].append(item["tag"])

        if item["io_type"]:
            by_io[
                item["io_type"]
            ].append(item["tag"])

        m = re.match(
            r"^([A-Z]+)",
            key
        )

        if m:
            by_prefix[m.group(1)] += 1

    # --------------------------------------------------------------
    # SOURCE MANIFEST
    # --------------------------------------------------------------

    source_paths = [
        PROJECT / "database/pci/pci_instrument_database.json",
        DOWNLOAD / "pci_instrument_database.csv",
        DOWNLOAD / "PCI PLC TOTAL IO.xlsx",
        DOWNLOAD / "PCI_INSTRUMENT_RANGE.xlsx",
        DOWNLOAD / "critical spares in pci.xlsx",
        DOWNLOAD / "MBF2  PCI  cable schedule .xlsx",
        DOWNLOAD / "MBF2  PCI  cable schedule  (1).xlsx",
    ]

    manifest = []

    for path in source_paths:

        if not path.exists():
            continue

        manifest.append({
            "file": str(path),
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        })

    # --------------------------------------------------------------
    # FINAL INDEX
    # --------------------------------------------------------------

    index = {
        "schema": "ANVIQO_ENGINEERING_KNOWLEDGE_INDEX_V1",
        "generated_at": build_time,

        "rules": {
            "read_only": True,
            "invent_data": False,
            "existing_v5_replaced": False,
            "existing_pci_registry_replaced": False,
            "source_values_preserved": True,
        },

        "summary": {
            "instrument_count": len(instruments),
            "range_links": range_links,
            "spare_links": spare_links,
            "cable_links": cable_links,
            "plc_links": plc_links,
            "areas": len(by_area),
            "panels": len(by_panel),
            "terminal_blocks": len(by_tb),
            "io_types": len(by_io),
        },

        "instruments": instruments,

        "indexes": {
            "by_area": dict(by_area),
            "by_panel": dict(by_panel),
            "by_tb": dict(by_tb),
            "by_io_type": dict(by_io),
            "tag_prefix_distribution": dict(by_prefix),
        },

        "sources": manifest,
    }

    output = OUT / "engineering_knowledge_index.json"

    output.write_text(
        json.dumps(
            index,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------------
    # HUMAN-READABLE SUMMARY
    # --------------------------------------------------------------

    summary = {
        "schema": index["schema"],
        "generated_at": build_time,
        "instrument_count": len(instruments),
        "range_links": range_links,
        "spare_links": spare_links,
        "cable_links": cable_links,
        "plc_links": plc_links,
        "areas": len(by_area),
        "panels": len(by_panel),
        "terminal_blocks": len(by_tb),
        "io_types": len(by_io),
        "top_prefixes": dict(
            by_prefix.most_common(30)
        ),
    }

    (OUT / "engineering_knowledge_summary.json").write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------------
    # BUILD REPORT
    # --------------------------------------------------------------

    report = []

    report.append("=" * 90)
    report.append("ANVIQO ENGINEERING KNOWLEDGE INDEX")
    report.append("=" * 90)
    report.append("")
    report.append("GENERATED: " + build_time)
    report.append("")
    report.append("MASTER INSTRUMENTS : " + str(len(instruments)))
    report.append("RANGE LINKS        : " + str(range_links))
    report.append("SPARE LINKS        : " + str(spare_links))
    report.append("CABLE LINKS        : " + str(cable_links))
    report.append("PLC LINKS          : " + str(plc_links))
    report.append("AREAS              : " + str(len(by_area)))
    report.append("PANELS             : " + str(len(by_panel)))
    report.append("TERMINAL BLOCKS    : " + str(len(by_tb)))
    report.append("I/O TYPES          : " + str(len(by_io)))
    report.append("")
    report.append("TOP TAG PREFIXES")
    report.append("-" * 90)

    for prefix, count in by_prefix.most_common(50):
        report.append(
            f"{prefix:25} {count}"
        )

    report.append("")
    report.append("SOURCE FILES")
    report.append("-" * 90)

    for source in manifest:
        report.append(
            f"{source['name']} | "
            f"{source['size']} bytes | "
            f"SHA256 {source['sha256'][:16]}..."
        )

    report.append("")
    report.append("=" * 90)
    report.append("ENGINEERING KNOWLEDGE INDEX BUILD COMPLETE")
    report.append("EXISTING PCI/V5 INTELLIGENCE PRESERVED")
    report.append("=" * 90)

    report_path = OUT / "engineering_knowledge_build_report.txt"

    report_path.write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    print()
    print("\n".join(report))

    print()
    print("INDEX:", output)
    print("SUMMARY:", OUT / "engineering_knowledge_summary.json")
    print("REPORT:", report_path)


if __name__ == "__main__":
    main()
