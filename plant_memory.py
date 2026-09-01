from pathlib import Path
from datetime import datetime, timezone
import json
import uuid
import re

ROOT = Path(__file__).resolve().parent
MEMORY_DIR = ROOT / "database" / "plant_memory"
MEMORY_FILE = MEMORY_DIR / "plant_memory.json"

def _now():
    return datetime.now(timezone.utc).isoformat()

def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()

def _load():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text(
            json.dumps({
                "version": "PLANT-MEMORY-1.0",
                "records": []
            }, indent=2),
            encoding="utf-8"
        )

    data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise RuntimeError("Invalid Plant Memory database")

    return data

def _save(data):
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
            "Plant Memory accepts verified=True records only."
        )

    if not str(event).strip():
        raise ValueError("event is required")

    if not str(source).strip():
        raise ValueError("source is required")

    return {
        "memory_id": "PM-" + uuid.uuid4().hex[:12].upper(),
        "timestamp": timestamp or _now(),
        "event": str(event).strip(),
        "equipment": str(equipment).strip(),
        "tag": str(tag).strip(),
        "area": str(area).strip(),
        "source": str(source).strip(),
        "observation": str(observation).strip(),
        "maintenance_action": str(maintenance_action).strip(),
        "finding": str(finding).strip(),
        "confirmation_evidence": str(confirmation_evidence).strip(),
        "outcome": str(outcome).strip(),
        "recovery_status": str(recovery_status).strip(),
        "spare_used": str(spare_used).strip(),
        "related_event_id": str(related_event_id).strip(),
        "related_maintenance_record": str(
            related_maintenance_record
        ).strip(),
        "notes": str(notes).strip(),
        "verified": True
    }

def store_memory(record):
    if not isinstance(record, dict):
        raise ValueError("Memory record must be a dictionary")

    if record.get("verified") is not True:
        raise ValueError("Rejected: memory is not verified")

    data = _load()

    data["records"].append(record)

    _save(data)

    return record

def search_memory(
    query="",
    tag="",
    equipment="",
    area="",
    limit=20
):
    data = _load()

    q = _norm(query)
    t = _norm(tag)
    e = _norm(equipment)
    a = _norm(area)

    results = []

    for record in reversed(data["records"]):

        if record.get("verified") is not True:
            continue

        searchable = _norm(" ".join([
            record.get("event", ""),
            record.get("observation", ""),
            record.get("maintenance_action", ""),
            record.get("finding", ""),
            record.get("outcome", ""),
            record.get("tag", ""),
            record.get("equipment", ""),
            record.get("area", ""),
            record.get("source", "")
        ]))

        if q and q not in searchable:
            continue

        if t and t not in _norm(record.get("tag")):
            continue

        if e and e not in _norm(record.get("equipment")):
            continue

        if a and a not in _norm(record.get("area")):
            continue

        results.append(record)

        if len(results) >= limit:
            break

    return results

def find_similar_events(
    event,
    tag="",
    equipment="",
    area="",
    limit=10
):
    terms = [
        x for x in re.findall(
            r"[a-z0-9_-]+",
            _norm(event)
        )
        if len(x) > 2
    ]

    candidates = search_memory(
        tag=tag,
        equipment=equipment,
        area=area,
        limit=10000
    )

    scored = []

    for record in candidates:

        text = _norm(" ".join([
            record.get("event", ""),
            record.get("observation", ""),
            record.get("finding", "")
        ]))

        score = sum(
            1 for term in terms
            if term in text
        )

        if score:
            scored.append((score, record))

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        record
        for score, record in scored[:limit]
    ]

def record_outcome(
    memory_id,
    outcome,
    recovery_status="",
    confirmation_evidence=""
):
    data = _load()

    for record in data["records"]:

        if record.get("memory_id") == memory_id:

            if not str(outcome).strip():
                raise ValueError(
                    "Verified outcome is required"
                )

            record["outcome"] = str(outcome).strip()

            if recovery_status:
                record["recovery_status"] = (
                    str(recovery_status).strip()
                )

            if confirmation_evidence:
                record["confirmation_evidence"] = (
                    str(confirmation_evidence).strip()
                )

            record["updated_at"] = _now()

            _save(data)

            return record

    raise KeyError(
        "Memory not found: " + str(memory_id)
    )

def health_check():

    data = _load()

    records = data.get("records", [])

    return {
        "module": "Plant Memory V1.0",
        "status": "PASS",
        "records": len(records),
        "verified_only": all(
            r.get("verified") is True
            for r in records
        ),
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "HUMAN_DECISION_REQUIRED": True
    }

if __name__ == "__main__":
    print(json.dumps(
        health_check(),
        indent=2
    ))
