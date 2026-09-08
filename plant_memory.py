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
    if verified not in (True, False):
        raise ValueError(
            "verified must be True or False"
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
        "verified": bool(verified),
        "verification_status": (
            "VERIFIED" if verified is True else "PENDING_VERIFICATION"
        )
    }

def store_memory(record):
    if not isinstance(record, dict):
        raise ValueError("Memory record must be a dictionary")

    # Conversationally supplied memories may be stored for later
    # human verification, but they are NEVER treated as verified
    # evidence until verified=True is explicitly recorded.
    if record.get("verified") not in (True, False):
        raise ValueError("verified must be True or False")

    if record.get("verified") is True:
        record["verification_status"] = "VERIFIED"
    else:
        record["verification_status"] = "PENDING_VERIFICATION"

    data = _load()

    # Duplicate protection: same tag + event + action + finding
    # is not inserted repeatedly.
    for existing in data["records"]:
        if (
            _norm(existing.get("tag")) == _norm(record.get("tag"))
            and _norm(existing.get("event")) == _norm(record.get("event"))
            and _norm(existing.get("maintenance_action"))
                == _norm(record.get("maintenance_action"))
            and _norm(existing.get("finding"))
                == _norm(record.get("finding"))
        ):
            return existing

    data["records"].append(record)

    _save(data)

    # ANVIQO_NEON_MEMORY_HOOK_V2
    try:
        from anvi_neon_store import upsert_memory
        upsert_memory(record)
    except Exception:
        pass

    return record


def create_conversational_memory(
    event,
    source,
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
    """
    Store user-supplied maintenance history.

    IMPORTANT:
    Conversationally supplied history is PENDING_VERIFICATION.
    It is never presented as verified evidence until a human
    verification step explicitly changes verified=True.
    """

    record = create_memory(
        event=event,
        source=source,
        verified=False,
        equipment=equipment,
        tag=tag,
        area=area,
        observation=observation,
        maintenance_action=maintenance_action,
        finding=finding,
        confirmation_evidence=confirmation_evidence,
        outcome=outcome,
        recovery_status=recovery_status,
        spare_used=spare_used,
        related_event_id=related_event_id,
        related_maintenance_record=related_maintenance_record,
        notes=notes
    )

    return store_memory(record)


def verify_memory(memory_id, notes=""):
    """
    Explicit human verification step.

    This is the ONLY path provided by this module for converting
    a pending conversational memory into verified memory.
    """

    data = _load()

    for record in data["records"]:
        if record.get("memory_id") == memory_id:
            record["verified"] = True
            record["verification_status"] = "VERIFIED"
            record["verified_at"] = _now()

            if notes:
                record["verification_notes"] = str(notes).strip()

            _save(data)
            return record

    raise KeyError("Memory not found: " + str(memory_id))


def search_all_memory(
    query="",
    tag="",
    equipment="",
    area="",
    limit=20
):
    """
    Internal/admin retrieval including pending memories.

    V2:
    - Uses tag/equipment as the primary identity constraint.
    - Uses token-overlap matching instead of requiring the complete
      question to occur verbatim inside the stored report.
    - Falls back to persistent Neon memory when local filesystem
      memory is unavailable or incomplete.
    - Keeps pending memories available for human-review workflows.
    """

    q = _norm(query)
    t = _norm(tag)
    e = _norm(equipment)
    a = _norm(area)

    stop_words = {
        "what", "when", "where", "which", "who", "why", "how",
        "did", "does", "do", "is", "was", "were", "are", "the",
        "this", "that", "last", "time", "about", "tell", "me",
        "show", "give", "report", "reports", "field", "memory",
        "maintenance", "find", "found", "happened", "happen",
        "with", "for", "from", "and", "or", "on", "in", "to",
        "of", "a", "an", "it", "its", "my", "our", "plant"
    }

    def tokens(value):
        return {
            x for x in re.findall(r"[a-z0-9]+", _norm(value))
            if len(x) > 2 and x not in stop_words
        }

    query_tokens = tokens(q)

    def matches(record):
        record_tag = _norm(record.get("tag"))
        record_equipment = _norm(record.get("equipment"))
        record_area = _norm(record.get("area"))

        if t and t not in record_tag and t not in record_equipment:
            return False

        if e and e not in record_equipment and e not in record_tag:
            return False

        if a and a not in record_area:
            return False

        searchable = _norm(" ".join([
            record.get("event", ""),
            record.get("observation", ""),
            record.get("maintenance_action", ""),
            record.get("finding", ""),
            record.get("confirmation_evidence", ""),
            record.get("outcome", ""),
            record.get("recovery_status", ""),
            record.get("spare_used", ""),
            record.get("tag", ""),
            record.get("equipment", ""),
            record.get("area", ""),
            record.get("source", ""),
            record.get("notes", "")
        ]))

        if not q:
            return True

        if q in searchable:
            return True

        if query_tokens:
            record_tokens = tokens(searchable)
            overlap = query_tokens & record_tokens

            # Identity-constrained queries such as
            # "what happened to PT-303 last time" should succeed
            # primarily from the verified equipment tag constraint.
            if (t or e) and len(overlap) >= 1:
                return True

            # General memory queries need meaningful overlap.
            if len(overlap) >= 2:
                return True

        return False

    def rank(record):
        searchable = _norm(" ".join([
            record.get("event", ""),
            record.get("observation", ""),
            record.get("maintenance_action", ""),
            record.get("finding", ""),
            record.get("confirmation_evidence", ""),
            record.get("outcome", ""),
            record.get("recovery_status", ""),
            record.get("spare_used", ""),
            record.get("tag", ""),
            record.get("equipment", ""),
            record.get("area", ""),
            record.get("source", ""),
            record.get("notes", "")
        ]))

        score = 0

        if t and t in _norm(record.get("tag")):
            score += 100

        if e and e in _norm(record.get("equipment")):
            score += 100

        if a and a in _norm(record.get("area")):
            score += 25

        if query_tokens:
            score += len(query_tokens & tokens(searchable)) * 10

        if record.get("source") == "technician field report":
            score += 5

        return score

    local_results = []

    try:
        data = _load()

        for record in reversed(data.get("records", [])):
            if matches(record):
                local_results.append(record)

            if len(local_results) >= limit:
                break

    except Exception:
        local_results = []

    # ------------------------------------------------------------
    # Persistent Neon fallback
    # ------------------------------------------------------------
    try:
        from anvi_neon_store import get_memory, neon_enabled

        if neon_enabled():
            neon_records = get_memory(
                tag=tag or "",
                equipment=equipment or ""
            )

            seen = {
                str(x.get("memory_id", ""))
                for x in local_results
            }

            for record in neon_records:
                if not isinstance(record, dict):
                    continue

                # Neon may contain the complete memory payload.
                if not matches(record):
                    continue

                memory_id = str(record.get("memory_id", ""))

                if memory_id and memory_id in seen:
                    continue

                local_results.append(record)

                if memory_id:
                    seen.add(memory_id)

                if len(local_results) >= limit:
                    break

    except Exception:
        # Persistent storage must never break ANVI's normal
        # read-only conversational service.
        pass

    local_results.sort(
        key=rank,
        reverse=True
    )

    return local_results[:limit]

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
