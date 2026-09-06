from pathlib import Path
import json
import re

INDEX = Path("database/engineering/index/engineering_knowledge_index.json")

def norm(v):
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())

def walk(obj, path="root"):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")

def find_exact(data, wanted):
    target = norm(wanted)
    hits = []

    for path, obj in walk(data):
        if not isinstance(obj, dict):
            continue

        for key, value in obj.items():
            if isinstance(value, (str, int, float)):
                if norm(value) == target:
                    hits.append({
                        "path": path,
                        "field": key,
                        "value": value,
                        "record": obj
                    })
    return hits

def find_partial(data, wanted):
    target = norm(wanted)
    hits = []

    for path, obj in walk(data):
        if not isinstance(obj, dict):
            continue

        for key, value in obj.items():
            if isinstance(value, (str, int, float)):
                nv = norm(value)

                if target and (target in nv or nv in target):
                    hits.append({
                        "path": path,
                        "field": key,
                        "value": value,
                        "record": obj
                    })
    return hits

def show(label, hits, limit=20):
    print()
    print("=" * 100)
    print(label)
    print("=" * 100)
    print("MATCHES:", len(hits))

    for h in hits[:limit]:
        print()
        print("PATH :", h["path"])
        print("FIELD:", h["field"])
        print("VALUE:", h["value"])
        print("RECORD:")
        print(json.dumps(h["record"], ensure_ascii=False))

def inspect(data):
    print()
    print("=" * 100)
    print("ENGINEERING INDEX STRUCTURE")
    print("=" * 100)

    collections = []

    def scan(obj, path="root"):
        if isinstance(obj, list) and obj:
            records = [x for x in obj[:20] if isinstance(x, dict)]

            if records:
                fields = set()
                for r in records:
                    fields.update(r.keys())

                collections.append(
                    (path, len(obj), sorted(map(str, fields)))
                )

        elif isinstance(obj, dict):
            for k, v in obj.items():
                scan(v, f"{path}.{k}")

    scan(data)

    for path, count, fields in collections:
        print()
        print("PATH:", path)
        print("COUNT:", count)
        print("FIELDS:")
        for f in fields:
            print("  ", f)

def main():
    if not INDEX.exists():
        print("ERROR: index does not exist:")
        print(INDEX)
        return

    data = json.loads(INDEX.read_text(encoding="utf-8"))

    inspect(data)

    for tag in ["PT303", "MCV201", "AT201", "LP_1_Healthy"]:
        show(
            "EXACT/NORMALIZED TAG: " + tag,
            find_exact(data, tag)
        )

    for q in ["PT", "MCV", "range", "spare", "PLC", "cable"]:
        show(
            "PARTIAL DISCOVERY: " + q,
            find_partial(data, q)
        )

    print()
    print("=" * 100)
    print("UNIVERSAL RESOLVER DIAGNOSTIC COMPLETE")
    print("NO EXISTING ANVIQO INTELLIGENCE MODIFIED")
    print("=" * 100)

if __name__ == "__main__":
    main()
