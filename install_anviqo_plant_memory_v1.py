from pathlib import Path
import json
from datetime import datetime, timezone
import uuid
import re

ROOT = Path.cwd()
MEMORY_DIR = ROOT / "database" / "plant_memory"
MEMORY_FILE = MEMORY_DIR / "plant_memory.json"
SCHEMA_FILE = MEMORY_DIR / "memory_schema.json"

def now():
    return datetime.now(timezone.utc).isoformat()

def norm(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()

def ensure_store():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text(
            json.dumps({
                "version": "PLANT-MEMORY-1.0",
                "records": []
            }, indent=2),
            encoding="utf-8"
        )

    schema = {
        "version": "PLANT-MEMORY-1.0",
        "policy": "verified_evidence_only",
        "required": [
            "event",
            "source",
            "verified"
        ],
        "safety": {
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True
        }
    }

    SCHEMA_FILE.write_text(
        json.dumps(schema, indent=2),
        encoding="utf-8"
    )

def load():
    ensure_store()
    return json.loads(
        MEMORY_FILE.read_text(encoding="utf-8")
    )

def save(data):
    tmp = MEMORY_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    tmp.replace(MEMORY_FILE)

def create_memory(
    event,
    source,
    verified,
    timestamp=None,
    equipment="",
    tag="",
    area="",
    observation="",
    maintenance_action="",
    finding="",
    confirmation_evidence="",
    outcome="",
    recovery_status="",
    spare_used="",
    related_event_id="",
    related_maintenance_record="",
    notes=""
):
    if verified is not True:
        raise ValueError(
            "Plant Memory accepts verified evidence only."
        )

    if not str(event).strip():
        raise ValueError("event is required")

    if not str(source).strip():
        raise ValueError("source is required")

    return {
        "memory_id":
            "PM-" + uuid.uuid4().hex[:12].upper(),

        "timestamp": timestamp or now(),

        "event": str(event).strip(),
        "equipment": str(equipment).strip(),
        "tag": str(tag).strip(),
        "area": str(area).strip(),

        "source": str(source).strip(),

        "observation": str(observation).strip(),

        "maintenance_action":
            str(maintenance_action).strip(),

        "finding": str(finding).strip(),

        "confirmation_evidence":
            str(confirmation_evidence).strip(),

        "outcome": str(outcome).strip(),

        "recovery_status":
            str(recovery_status).strip(),

        "spare_used":
            str(spare_used).strip(),

        "related_event_id":
            str(related_event_id).strip(),

        "related_maintenance_record":
            str(related_maintenance_record).strip(),

        "notes": str(notes).strip(),

        "verified": True
    }

def store_memory(record):
    if record.get("verified") is not True:
        raise ValueError(
            "Rejected: unverified memory."
        )

    data = load()

    data["records"].append(record)

    save(data)

    return record

def search_memory(
    query="",
    tag="",
    equipment="",
    area="",
    limit=20
):
    data = load()

    q = norm(query)
    t = norm(tag)
    e = norm(equipment)
    a = norm(area)

    results = []

    for record in reversed(data["records"]):

        if record.get("verified") is not True:
            continue

        searchable = norm(" ".join([
            record.get("event", ""),
            record.get("observation", ""),
            record.get("maintenance_action", ""),
            record.get("finding", ""),
            record.get("outcome", ""),
            record.get("tag", ""),
            record.get("equipment", ""),
            record.get("area", "")
        ]))

        if q and q not in searchable:
            continue

        if t and t not in norm(record.get("tag")):
            continue

        if e and e not in norm(record.get("equipment")):
            continue

        if a and a not in norm(record.get("area")):
            continue

        results.append(record)

        if len(results) >= limit:
            break

    return results

def health_check():
    data = load()

    records = data.get("records", [])

    return {
        "module": "Plant Memory V1.0",
        "status": "PASS",
        "records": len(records),
        "verified_only":
            all(
                r.get("verified") is True
                for r in records
            ),
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "HUMAN_DECISION_REQUIRED": True
    }

if __name__ == "__main__":

    print()
    print("==========================================")
    print(" ANVIQO PLANT MEMORY V1.0 INSTALL")
    print("==========================================")

    ensure_store()

    result = health_check()

    print(json.dumps(result, indent=2))

    print()
    print("Memory database:")
    print(MEMORY_FILE)

    print()
    print("Schema:")
    print(SCHEMA_FILE)

    print()
    print("V5 / PCI intelligence modified: FALSE")
    print("PLC write enabled: FALSE")
    print("SCADA control enabled: FALSE")
    print("==========================================")
