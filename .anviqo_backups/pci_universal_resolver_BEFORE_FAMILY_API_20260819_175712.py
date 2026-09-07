
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
