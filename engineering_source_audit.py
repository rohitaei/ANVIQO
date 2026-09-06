from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import csv
import json
import re
import shutil
import subprocess

DOWNLOAD = Path("/storage/emulated/0/Download")
OUT = Path("database/engineering/audit")
OUT.mkdir(parents=True, exist_ok=True)

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}

def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()

def xlsx_sheets(path):
    with ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))

        relmap = {}
        for r in rels:
            relmap[r.attrib.get("Id")] = r.attrib.get("Target", "")

        result = []

        for s in wb.find("main:sheets", NS):
            name = s.attrib.get("name", "")
            rid = s.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            target = relmap.get(rid, "")

            if target.startswith("/"):
                target = target[1:]

            if not target.startswith("xl/"):
                target = "xl/" + target

            result.append((name, target))

        return result

def xlsx_preview(path, target, max_rows=15):
    with ZipFile(path) as z:

        shared = []

        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))

            for si in root.findall("main:si", NS):
                text = "".join(
                    t.text or ""
                    for t in si.iter("{%s}t" % NS["main"])
                )
                shared.append(text)

        root = ET.fromstring(z.read(target))

        output = []

        for row in root.findall(".//main:sheetData/main:row", NS):
            cells = {}

            for c in row.findall("main:c", NS):
                ref = c.attrib.get("r", "")
                m = re.match(r"([A-Z]+)", ref)

                if not m:
                    continue

                col = m.group(1)
                typ = c.attrib.get("t")
                vnode = c.find("main:v", NS)

                if typ == "inlineStr":
                    value = "".join(
                        t.text or ""
                        for t in c.iter("{%s}t" % NS["main"])
                    )

                elif vnode is None:
                    value = ""

                else:
                    value = vnode.text or ""

                    if typ == "s":
                        try:
                            value = shared[int(value)]
                        except Exception:
                            pass

                    elif typ == "b":
                        value = "TRUE" if value == "1" else "FALSE"

                cells[col] = clean(value)

            if cells:
                output.append(cells)

            if len(output) >= max_rows:
                break

        columns = sorted(
            {c for row in output for c in row},
            key=lambda c: (
                sum((ord(x) - 64) * 26 ** i
                    for i, x in enumerate(reversed(c)))
            )
        )

        return [
            [row.get(c, "") for c in columns]
            for row in output
        ]

def inspect_xlsx(path):
    print("\n" + "=" * 100)
    print("XLSX:", path)
    print("SIZE:", path.stat().st_size, "bytes")
    print("=" * 100)

    try:
        sheets = xlsx_sheets(path)
    except Exception as e:
        print("ERROR:", repr(e))
        return

    print("SHEETS:", len(sheets))

    for number, (name, target) in enumerate(sheets, 1):
        print("\n--- SHEET", number, ":", name, "---")
        print("TARGET:", target)

        try:
            rows = xlsx_preview(path, target)

            print("PREVIEW ROWS:", len(rows))

            for row in rows:
                print(" | ".join(row))

        except Exception as e:
            print("SHEET ERROR:", repr(e))

def inspect_csv(path):
    print("\n" + "=" * 100)
    print("CSV:", path)
    print("SIZE:", path.stat().st_size, "bytes")
    print("=" * 100)

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace"
        ) as f:
            reader = csv.reader(f)

            for i, row in enumerate(reader):
                print(" | ".join(clean(x) for x in row))

                if i >= 15:
                    break

    except Exception as e:
        print("CSV ERROR:", repr(e))

def inspect_json(path):
    print("\n" + "=" * 100)
    print("JSON:", path)
    print("=" * 100)

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        )

        print("TYPE:", type(data).__name__)

        if isinstance(data, list):
            print("COUNT:", len(data))

            if data:
                print("FIRST RECORD:")
                print(json.dumps(
                    data[0],
                    indent=2,
                    ensure_ascii=False
                ))

        elif isinstance(data, dict):
            print("KEYS:", list(data.keys())[:100])

    except Exception as e:
        print("JSON ERROR:", repr(e))

def inspect_docx(path):
    print("\n" + "=" * 100)
    print("DOCX:", path)
    print("SIZE:", path.stat().st_size, "bytes")
    print("=" * 100)

    try:
        with ZipFile(path) as z:
            xml = z.read("word/document.xml")

        root = ET.fromstring(xml)

        texts = []

        for p in root.iter(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
        ):
            parts = []

            for t in p.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            ):
                parts.append(t.text or "")

            line = clean("".join(parts))

            if line:
                texts.append(line)

        print("PARAGRAPHS:", len(texts))

        for line in texts[:120]:
            print(line)

    except Exception as e:
        print("DOCX ERROR:", repr(e))

def pdf_tools():
    print("\n" + "=" * 100)
    print("PDF TOOL AVAILABILITY")
    print("=" * 100)

    for tool in [
        "pdftotext",
        "pdfinfo",
        "mutool",
        "qpdf",
        "libreoffice",
        "soffice"
    ]:
        print(tool, "=>", shutil.which(tool) or "NOT FOUND")

def inspect_pdf(path):
    print("\n" + "=" * 100)
    print("PDF:", path)
    print("SIZE:", path.stat().st_size, "bytes")
    print("=" * 100)

    tool = shutil.which("pdftotext")

    if not tool:
        print("PDF TEXT EXTRACTION NOT AVAILABLE")
        return

    target = OUT / (path.stem.replace(" ", "_") + "_text.txt")

    try:
        subprocess.run(
            [
                tool,
                "-layout",
                str(path),
                str(target)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )

        if target.exists():
            text = target.read_text(
                encoding="utf-8",
                errors="replace"
            )

            print("EXTRACTED:", len(text), "characters")
            print(text[:12000])

    except Exception as e:
        print("PDF ERROR:", repr(e))

def main():

    print("=" * 100)
    print("ANVIQO ENGINEERING KNOWLEDGE")
    print("SOURCE FORENSIC AUDIT")
    print("=" * 100)

    print("PROJECT:", Path(".").resolve())
    print("DOWNLOAD:", DOWNLOAD)

    pdf_tools()

    xlsx_files = [
        DOWNLOAD / "PCI PLC TOTAL IO.xlsx",
        DOWNLOAD / "PCI_INSTRUMENT_RANGE.xlsx",
        DOWNLOAD / "critical spares in pci.xlsx",
        DOWNLOAD / "MBF2  PCI  cable schedule .xlsx",
        DOWNLOAD / "MBF2  PCI  cable schedule  (1).xlsx",
    ]

    csv_files = [
        DOWNLOAD / "pci_instrument_database.csv",
        DOWNLOAD / "pci_instrument_database-1.csv",
    ]

    json_files = [
        DOWNLOAD / "pci_instrument_database.json",
        Path("database/pci/pci_instrument_database.json"),
    ]

    docx_files = [
        DOWNLOAD / "PCI-Process Control Philosophy.docx",
    ]

    pdf_files = [
        DOWNLOAD / "TMLPCI-ANDE-00-PRO-BE-E0003-01-8_P&IDiagramforPCIUnit_20082018-Model.pdf",
        DOWNLOAD / "PCI-Process Control Philosophy.pdf",
        DOWNLOAD / "SOPFORPLCANDDCS.pdf",
        DOWNLOAD / "WORKINGINPLC.pdf",
        DOWNLOAD / "TMLPCI-ANDE-15-INS-DE-D0055-01-0.pdf",
    ]

    print("\n===== ENGINEERING XLSX SOURCES =====")

    for path in xlsx_files:
        if path.exists():
            inspect_xlsx(path)
        else:
            print("MISSING:", path)

    print("\n===== CSV SOURCES =====")

    for path in csv_files:
        if path.exists():
            inspect_csv(path)

    print("\n===== JSON SOURCES =====")

    for path in json_files:
        if path.exists():
            inspect_json(path)

    print("\n===== DOCX SOURCES =====")

    for path in docx_files:
        if path.exists():
            inspect_docx(path)

    print("\n===== PDF SOURCES =====")

    for path in pdf_files:
        if path.exists():
            inspect_pdf(path)

    print("\n" + "=" * 100)
    print("SOURCE FORENSIC AUDIT COMPLETE")
    print("NO PCI/V5 INTELLIGENCE WAS MODIFIED")
    print("=" * 100)

if __name__ == "__main__":
    main()
