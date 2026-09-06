import json
import re
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(".")
DB = ROOT / "database/pci/pci_instrument_database.json"
KNOW = ROOT / "anvi_knowledge_layer.py"
PCI = ROOT / "pci_conversation.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def norm(v):
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())

def load():
    with open(DB, encoding="utf-8") as f:
        db = json.load(f)
    return db, db["records"]

def family_keys(r):
    """
    Database-driven family extraction.
    No hard-coded equipment prefix list.
    """
    result = set()

    tag = str(r.get("tag", "")).strip()
    fox = str(r.get("fox_plc_tag", "")).strip()
    desc = str(r.get("description", "")).strip()

    if fox:
        result.add(norm(fox))

    if tag:
        nt = norm(tag)
        result.add(nt)

        parts = re.split(r"[_\-\s]+", tag.upper())

        # Only signal/function suffixes are removed.
        suffixes = {
            "HEALTHY",
            "CONTROL_ON",
            "EPB",
            "REMOTE_FB",
            "FWD",
            "REV",
            "TRIP_FB",
            "TRQ",
            "OP_FB",
            "CLS_FB",
            "FWD_CMD",
            "REV_CMD",
            "LOCAL_PER",
        }

        for i in range(1, len(parts)):
            candidate = norm("_".join(parts[:i]))
            suffix = "_".join(parts[i:])

            if candidate and suffix in suffixes:
                result.add(candidate)

    # Evidence-derived relation from description.
    nd = norm(desc)

    for value in (tag, fox):
        nv = norm(value)
        if nv and nv in nd:
            result.add(nv)

    return {x for x in result if x}

def build_index(records):
    exact = {}
    families = {}

    for r in records:
        tag = str(r.get("tag", "")).strip()

        if tag:
            exact.setdefault(norm(tag), []).append(r)

        for key in family_keys(r):
            families.setdefault(key, []).append(r)

    return exact, families

def resolve(query, records):
    exact, families = build_index(records)

    q = str(query or "").strip()
    nq = norm(q)

    if not nq:
        return [], None

    # Exact verified tag.
    if nq in exact:
        return exact[nq], "EXACT"

    # Exact verified family.
    if nq in families:
        return families[nq], "FAMILY"

    # Embedded verified family.
    candidates = []

    for key, rows in families.items():
        if len(key) >= 3 and key in nq:
            candidates.append((len(key), rows, key))

    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1], "FAMILY"

    # Natural language spacing:
    # MCV 204 -> MCV204
    tokens = [
        norm(x)
        for x in re.findall(r"[A-Za-z0-9]+", q)
        if norm(x)
    ]

    if len(tokens) >= 2:
        compact = "".join(tokens)

        if compact in families:
            return families[compact], "FAMILY"

    return [], None

def backup(path):
    if path.exists():
        target = path.with_name(
            path.stem +
            "_BEFORE_UNIVERSAL_PCI_FAMILY_" +
            STAMP +
            path.suffix
        )
        shutil.copy2(path, target)
        print("BACKUP:", target.name)

def install_resolver():
    target = ROOT / "pci_universal_resolver.py"

    target.write_text(r'''
import json
import re
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parent /
    "database/pci/pci_instrument_database.json"
)

def normalize(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

def load_records():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)["records"]

def family_keys(r):
    result = set()

    tag = str(r.get("tag", "")).strip()
    fox = str(r.get("fox_plc_tag", "")).strip()
    desc = str(r.get("description", "")).strip()

    if fox:
        result.add(normalize(fox))

    if tag:
        result.add(normalize(tag))

        parts = re.split(r"[_\-\s]+", tag.upper())

        suffixes = {
            "HEALTHY",
            "CONTROL_ON",
            "EPB",
            "REMOTE_FB",
            "FWD",
            "REV",
            "TRIP_FB",
            "TRQ",
            "OP_FB",
            "CLS_FB",
            "FWD_CMD",
            "REV_CMD",
            "LOCAL_PER",
        }

        for i in range(1, len(parts)):
            base = normalize("_".join(parts[:i]))
            suffix = "_".join(parts[i:])

            if base and suffix in suffixes:
                result.add(base)

    nd = normalize(desc)

    for value in (tag, fox):
        nv = normalize(value)
        if nv and nv in nd:
            result.add(nv)

    return {x for x in result if x}

def build_index(records=None):
    records = load_records() if records is None else records

    exact = {}
    families = {}

    for r in records:
        tag = str(r.get("tag", "")).strip()

        if tag:
            exact.setdefault(normalize(tag), []).append(r)

        for key in family_keys(r):
            families.setdefault(key, []).append(r)

    return exact, families

def resolve(query, records=None):
    exact, families = build_index(records)

    q = str(query or "").strip()
    nq = normalize(q)

    if not nq:
        return [], None

    if nq in exact:
        return exact[nq], "EXACT"

    if nq in families:
        return families[nq], "FAMILY"

    candidates = []

    for key, rows in families.items():
        if len(key) >= 3 and key in nq:
            candidates.append((len(key), rows))

    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1], "FAMILY"

    tokens = [
        normalize(x)
        for x in re.findall(r"[A-Za-z0-9]+", q)
        if normalize(x)
    ]

    if len(tokens) >= 2:
        compact = "".join(tokens)

        if compact in families:
            return families[compact], "FAMILY"

    return [], None

def group_io(records):
    groups = {
        "DI": [],
        "DO": [],
        "AI": [],
        "AO": [],
        "OTHER": []
    }

    for r in records:
        io = str(r.get("io_type", "")).upper().strip()

        if io.startswith("AI"):
            groups["AI"].append(r)
        elif io == "DI":
            groups["DI"].append(r)
        elif io == "DO":
            groups["DO"].append(r)
        elif io == "AO":
            groups["AO"].append(r)
        else:
            groups["OTHER"].append(r)

    return groups
''', encoding="utf-8")

    print("CREATED:", target)

def replace_function(text, name, replacement):
    pattern = re.compile(
        rf"(?ms)^def {re.escape(name)}\(.*?(?=^def |\Z)"
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "Could not locate function: " + name
        )

    return (
        text[:match.start()] +
        replacement.rstrip() +
        "\n\n" +
        text[match.end():]
    )

def patch_knowledge():
    text = KNOW.read_text(encoding="utf-8")

    if "pci_universal_resolver" not in text:
        text = (
            "from pci_universal_resolver import resolve as "
            "_universal_pci_resolve\n"
            + text
        )

    replacement = r'''def _tag_from_question(q):
    """
    UNIVERSAL VERIFIED PCI RESOLUTION.

    Resolves:
      1. exact verified tag
      2. verified equipment family
      3. natural-language formatting

    Never invents a tag.
    """
    records = _records()

    rows, mode = _universal_pci_resolve(q, records)

    if not rows:
        return None, None

    return rows[0].get("tag"), rows[0]
'''

    text = replace_function(
        text,
        "_tag_from_question",
        replacement
    )

    KNOW.write_text(text, encoding="utf-8")
    print("PATCHED:", KNOW)

def patch_pci():
    text = PCI.read_text(encoding="utf-8")

    if "pci_universal_resolver" not in text:
        text = (
            "from pci_universal_resolver import resolve as "
            "_universal_pci_resolve\n"
            + text
        )

    replacement = r'''def _find_tag_in_question(q):
    """
    UNIVERSAL VERIFIED PCI TAG/FAMILY RESOLUTION.
    """
    rows, mode = _universal_pci_resolve(q)

    if not rows:
        return None

    return rows[0]
'''

    text = replace_function(
        text,
        "_find_tag_in_question",
        replacement
    )

    PCI.write_text(text, encoding="utf-8")
    print("PATCHED:", PCI)

def audit():
    db, records = load()

    exact, families = build_index(records)

    print()
    print("===== FULL PCI AUDIT =====")
    print("DATABASE RECORDS :", len(records))
    print(
        "UNIQUE TAGS      :",
        len({
            str(r.get("tag", "")).strip()
            for r in records
            if str(r.get("tag", "")).strip()
        })
    )
    print("FAMILY INDEX     :", len(families))

    print()
    print("===== EQUIPMENT FAMILY TEST =====")

    tests = [
        "MCV 201",
        "MCV-201",
        "MCV201",
        "MCV 202",
        "MCV-202",
        "MCV202",
        "MCV 203",
        "MCV-203",
        "MCV203",
        "MCV 204",
        "MCV-204",
        "MCV204",
        "MCV 205",
        "MCV-205",
        "MCV205",
        "MCV 206",
        "MCV-206",
        "MCV206",
        "ZT_204",
        "AO_204",
        "MCV_204_FWD_Cmd",
    ]

    failures = []

    for q in tests:
        rows, mode = resolve(q, records)

        print(
            f"{q:24} "
            f"{mode or 'FAIL':7} "
            f"{len(rows):4} records"
        )

        if not rows:
            failures.append(q)

    print()
    print("===== EVERY DATABASE TAG TEST =====")

    unresolved = []

    for r in records:
        tag = str(r.get("tag", "")).strip()

        if not tag:
            continue

        rows, mode = resolve(tag, records)

        if not rows:
            unresolved.append(tag)

    print(
        "NONEMPTY TAG RECORDS:",
        sum(
            bool(str(r.get("tag", "")).strip())
            for r in records
        )
    )

    print("UNRESOLVED TAGS:", len(unresolved))

    if unresolved:
        for tag in unresolved[:100]:
            print("UNRESOLVED:", tag)

    print()
    print("===== MCV FAMILY I/O COVERAGE =====")

    for family in [
        "MCV 201",
        "MCV 202",
        "MCV 203",
        "MCV 204",
        "MCV 205",
        "MCV 206",
    ]:
        rows, _ = resolve(family, records)

        counts = {}

        for r in rows:
            io = str(r.get("io_type", "")).upper()
            counts[io] = counts.get(io, 0) + 1

        print(
            family,
            "TOTAL=", len(rows),
            counts
        )

    if failures or unresolved:
        print()
        print("STATUS: FAIL")
        print("DO NOT PUSH.")
        raise SystemExit(2)

    print()
    print("STATUS: PASS")
    print("ALL VERIFIED NONEMPTY PCI TAGS RESOLVE.")
    print("UNIVERSAL FAMILY RESOLUTION PASSED.")

def main():
    db, records = load()

    print("PCI SOURCE:", DB)
    print("PCI RECORDS:", len(records))

    if len(records) != 1064:
        raise RuntimeError(
            "Expected 1064 PCI records; found "
            + str(len(records))
        )

    backup(KNOW)
    backup(PCI)

    install_resolver()
    patch_knowledge()
    patch_pci()

    audit()

if __name__ == "__main__":
    main()
