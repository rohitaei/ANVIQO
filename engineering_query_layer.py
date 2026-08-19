"""
ANVIQO ENGINEERING KNOWLEDGE QUERY LAYER
========================================

Step 2 of the Engineering Knowledge reconstruction.

Purpose:
- Query the unified engineering knowledge index.
- Answer instrument / range / spare / cable / PLC questions.
- Preserve source provenance.
- Never invent engineering values.
- Read-only.
- Does NOT replace PCI/V5 reasoning.
"""

from pathlib import Path
import json
import re

INDEX = Path(
    "database/engineering/index/engineering_knowledge_index.json"
)

SUMMARY = Path(
    "database/engineering/index/engineering_knowledge_summary.json"
)


def load_json(path):
    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        )
    except Exception:
        return None


def load_index():
    data = load_json(INDEX)

    if data is None:
        raise RuntimeError(
            "Engineering Knowledge Index not found or invalid: "
            + str(INDEX)
        )

    return data


def normalize(value):
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        str(value or "").upper()
    )


def flatten_records(obj):
    """
    Find record-like lists anywhere inside the generated index.

    This makes the query layer tolerant of the exact index layout
    while preserving the original source records.
    """

    found = []

    def walk(value, path="root"):

        if isinstance(value, list):

            if value and all(
                isinstance(x, dict)
                for x in value[:min(len(value), 10)]
            ):
                found.append(
                    (
                        path,
                        value
                    )
                )

            for i, item in enumerate(value):
                walk(item, f"{path}[{i}]")

        elif isinstance(value, dict):

            for key, item in value.items():
                walk(item, f"{path}.{key}")

    walk(obj)

    # Deduplicate by object identity.
    unique = []
    seen = set()

    for path, records in found:
        marker = id(records)

        if marker not in seen:
            seen.add(marker)
            unique.append((path, records))

    return unique


def identify_collections(index):
    """
    Classify record collections using field names and collection names.
    """

    collections = {
        "instrument": [],
        "range": [],
        "spare": [],
        "cable": [],
        "plc": [],
        "other": [],
    }

    for path, records in flatten_records(index):

        lower_path = path.lower()

        sample = records[:20]

        fields = set()

        for r in sample:
            fields.update(
                str(k).lower()
                for k in r.keys()
            )

        if (
            "range" in lower_path
            or "instrument_range" in lower_path
            or any(
                x in fields
                for x in (
                    "range",
                    "range_min",
                    "range_max",
                    "unit",
                    "engineering_unit",
                )
            )
        ):
            collections["range"].append(
                (path, records)
            )

        elif (
            "spare" in lower_path
            or any(
                x in fields
                for x in (
                    "spare",
                    "stock",
                    "quantity",
                    "available",
                    "material",
                )
            )
        ):
            collections["spare"].append(
                (path, records)
            )

        elif (
            "cable" in lower_path
            or any(
                x in fields
                for x in (
                    "cable",
                    "core",
                    "size",
                    "from",
                    "to",
                )
            )
        ):
            collections["cable"].append(
                (path, records)
            )

        elif (
            "plc" in lower_path
            or any(
                x in fields
                for x in (
                    "plc_address",
                    "plc_tag",
                    "fox_plc_tag",
                    "io_address",
                )
            )
        ):
            collections["plc"].append(
                (path, records)
            )

        elif (
            "instrument" in lower_path
            or "pci" in lower_path
            or any(
                x in fields
                for x in (
                    "tag",
                    "description",
                    "area",
                    "panel",
                    "tb_name",
                    "io_type",
                )
            )
        ):
            collections["instrument"].append(
                (path, records)
            )

        else:
            collections["other"].append(
                (path, records)
            )

    return collections


def record_text(record):
    return " | ".join(
        f"{k}={v}"
        for k, v in record.items()
        if v not in ("", None, [])
    )


def record_matches_tag(record, tag):
    target = normalize(tag)

    for key, value in record.items():

        key_norm = normalize(key)

        if key_norm in (
            "TAG",
            "INSTRUMENTTAG",
            "INSTRUMENT",
            "ITEMTAG",
            "PLCTAG",
            "FOXPLCTAG",
        ):

            if normalize(value) == target:
                return True

    return False


def find_tag_everywhere(index, tag):
    matches = []

    for path, records in flatten_records(index):

        for record in records:

            if record_matches_tag(record, tag):
                matches.append(
                    {
                        "collection": path,
                        "record": record,
                    }
                )

    return matches


def search_text(records, terms):
    result = []

    for record in records:

        text = " ".join(
            str(v)
            for v in record.values()
        ).upper()

        if all(
            normalize(term) in normalize(text)
            for term in terms
            if term
        ):
            result.append(record)

    return result


def query_instruments(index, question):

    collections = identify_collections(index)

    records = []

    for _, collection in collections["instrument"]:
        records.extend(collection)

    q = question.lower()

    # Exact tag first.
    tag_patterns = [
        r"\b[A-Z]{1,12}[-_]?\d{1,6}\b",
        r"\b[A-Z]{2,12}[-_]?[A-Z0-9_-]{2,20}\b",
    ]

    possible_tags = []

    for pattern in tag_patterns:
        possible_tags.extend(
            re.findall(
                pattern,
                question.upper()
            )
        )

    for tag in possible_tags:

        matches = [
            r for r in records
            if record_matches_tag(r, tag)
        ]

        if matches:
            return matches

    # General text search.
    terms = [
        x for x in re.findall(
            r"[A-Za-z0-9_-]+",
            q
        )
        if len(x) >= 3
    ]

    scored = []

    for record in records:

        text = record_text(record).lower()

        score = sum(
            1
            for term in terms
            if term in text
        )

        if score:
            scored.append(
                (
                    score,
                    record
                )
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        r for _, r in scored[:20]
    ]


def query_range(index, tag=None, question=""):

    collections = identify_collections(index)

    records = []

    for _, collection in collections["range"]:
        records.extend(collection)

    if tag:

        matches = [
            r for r in records
            if record_matches_tag(r, tag)
        ]

        if matches:
            return matches

    terms = [
        x
        for x in re.findall(
            r"[A-Za-z0-9_-]+",
            question
        )
        if len(x) >= 3
    ]

    return search_text(
        records,
        terms
    )[:20]


def query_spares(index, tag=None, question=""):

    collections = identify_collections(index)

    records = []

    for _, collection in collections["spare"]:
        records.extend(collection)

    if tag:

        matches = [
            r for r in records
            if record_matches_tag(r, tag)
        ]

        if matches:
            return matches

    terms = [
        x
        for x in re.findall(
            r"[A-Za-z0-9_-]+",
            question
        )
        if len(x) >= 3
    ]

    return search_text(
        records,
        terms
    )[:50]


def query_cables(index, tag=None, question=""):

    collections = identify_collections(index)

    records = []

    for _, collection in collections["cable"]:
        records.extend(collection)

    if tag:

        matches = [
            r for r in records
            if record_matches_tag(r, tag)
        ]

        if matches:
            return matches

    terms = [
        x
        for x in re.findall(
            r"[A-Za-z0-9_-]+",
            question
        )
        if len(x) >= 3
    ]

    return search_text(
        records,
        terms
    )[:50]


def query_plc(index, tag=None, question=""):

    collections = identify_collections(index)

    records = []

    for _, collection in collections["plc"]:
        records.extend(collection)

    if tag:

        matches = [
            r for r in records
            if record_matches_tag(r, tag)
        ]

        if matches:
            return matches

    terms = [
        x
        for x in re.findall(
            r"[A-Za-z0-9_-]+",
            question
        )
        if len(x) >= 3
    ]

    return search_text(
        records,
        terms
    )[:50]


def extract_tag(question):

    q = str(question or "").upper()

    # Prefer common engineering tag formats.
    patterns = [
        r"\b(?:PT|FT|LT|TT|TE|AT|ZT|PCV|FCV|MCV|FSV|BHV|WF|VRM|SAC|PSV|MSV)[-_]?[A-Z0-9]+\b",
        r"\b[A-Z]{1,12}[-_]?[0-9]{1,6}\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            q
        )

        if match:
            return match.group(0)

    return None


def answer(question):

    index = load_index()

    q = str(question or "").strip()
    ql = q.lower()

    if not q:
        return {
            "answer": "Please ask an engineering question.",
            "records": [],
            "source": "engineering knowledge index",
        }

    tag = extract_tag(q)

    # ------------------------------------------------------------
    # SPARES
    # ------------------------------------------------------------

    if any(
        word in ql
        for word in (
            "spare",
            "spares",
            "stock",
            "available",
            "availability",
        )
    ):

        records = query_spares(
            index,
            tag=tag,
            question=q
        )

        if records:

            return {
                "answer": (
                    f"I found {len(records)} verified engineering "
                    f"spare record(s)"
                    + (f" associated with {tag}." if tag else ".")
                ),
                "records": records[:50],
                "source": "engineering knowledge index / spare source",
            }

        return {
            "answer": (
                "I could not find a verified spare record for "
                + (tag if tag else "that query")
                + ". I will not invent availability."
            ),
            "records": [],
            "source": "engineering knowledge index / spare source",
        }

    # ------------------------------------------------------------
    # RANGE
    # ------------------------------------------------------------

    if any(
        word in ql
        for word in (
            "range",
            "measuring range",
            "measurement range",
            "calibration range",
            "span",
            "unit",
        )
    ):

        records = query_range(
            index,
            tag=tag,
            question=q
        )

        if records:

            return {
                "answer": (
                    f"I found {len(records)} verified range record(s)"
                    + (f" for {tag}." if tag else ".")
                ),
                "records": records[:20],
                "source": "engineering knowledge index / range source",
            }

        return {
            "answer": (
                "I could not find a verified range record for "
                + (tag if tag else "that query")
                + ". I will not invent a range."
            ),
            "records": [],
            "source": "engineering knowledge index / range source",
        }

    # ------------------------------------------------------------
    # CABLE
    # ------------------------------------------------------------

    if any(
        word in ql
        for word in (
            "cable",
            "core",
            "cabling",
            "termination",
            "from where",
            "to where",
        )
    ):

        records = query_cables(
            index,
            tag=tag,
            question=q
        )

        if records:

            return {
                "answer": (
                    f"I found {len(records)} verified cable record(s)"
                    + (f" associated with {tag}." if tag else ".")
                ),
                "records": records[:50],
                "source": "engineering knowledge index / cable schedule",
            }

        return {
            "answer": (
                "I could not find a verified cable record for "
                + (tag if tag else "that query")
                + "."
            ),
            "records": [],
            "source": "engineering knowledge index / cable schedule",
        }

    # ------------------------------------------------------------
    # PLC
    # ------------------------------------------------------------

    if any(
        word in ql
        for word in (
            "plc",
            "plc address",
            "io address",
            "fox plc",
            "input",
            "output",
        )
    ):

        records = query_plc(
            index,
            tag=tag,
            question=q
        )

        if records:

            return {
                "answer": (
                    f"I found {len(records)} verified PLC record(s)"
                    + (f" for {tag}." if tag else ".")
                ),
                "records": records[:50],
                "source": "engineering knowledge index / PLC source",
            }

        return {
            "answer": (
                "I could not find a verified PLC record for "
                + (tag if tag else "that query")
                + "."
            ),
            "records": [],
            "source": "engineering knowledge index / PLC source",
        }

    # ------------------------------------------------------------
    # GENERAL INSTRUMENT
    # ------------------------------------------------------------

    records = query_instruments(
        index,
        q
    )

    if records:

        return {
            "answer": (
                f"I found {len(records)} verified engineering "
                "instrument record(s)."
            ),
            "records": records[:20],
            "source": "engineering knowledge index / PCI source",
        }

    return {
        "answer": (
            "I could not find a verified engineering record for "
            "that question. I will not invent plant information."
        ),
        "records": [],
        "source": "engineering knowledge index",
    }


if __name__ == "__main__":

    print("=" * 90)
    print("ANVIQO ENGINEERING KNOWLEDGE QUERY LAYER")
    print("=" * 90)

    tests = [
        "What is the range of PT303?",
        "Is PT303 spare available?",
        "Show me spares for PT",
        "What is the PLC address of MCV201?",
        "Tell me about PT303",
        "Show cable information for PT303",
    ]

    for question in tests:

        print()
        print("-" * 90)
        print("QUESTION:", question)

        try:

            result = answer(question)

            print("ANSWER:")
            print(result["answer"])

            print("SOURCE:")
            print(result["source"])

            print("RECORDS:", len(result["records"]))

            for record in result["records"][:3]:
                print(
                    json.dumps(
                        record,
                        ensure_ascii=False
                    )
                )

        except Exception as exc:

            print(
                "QUERY ERROR:",
                repr(exc)
            )

    print()
    print("=" * 90)
    print("ENGINEERING QUERY LAYER TEST COMPLETE")
    print("NO EXISTING PCI/V5 INTELLIGENCE MODIFIED")
    print("=" * 90)
