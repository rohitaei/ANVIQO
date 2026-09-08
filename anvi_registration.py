# ANVIQO Smart Equipment & Spare Registration V1.0
# Safety: registration/database operation only. No PLC write. No SCADA control.
# New records are PENDING_VERIFICATION until explicitly verified by a human.

from pathlib import Path
import json
import re
from datetime import datetime

BASE = Path(__file__).resolve().parent

# ANVIQO OPERATIONAL DATA STORAGE V1
# Render Persistent Disk: /var/data
# Local development fallback: repository/database
_RENDER_DATA = Path("/var/data")
if _RENDER_DATA.exists() and _RENDER_DATA.is_dir() and _RENDER_DATA.is_writable():
    DATA_ROOT = _RENDER_DATA
else:
    DATA_ROOT = BASE / "database"

REG_DB = DATA_ROOT / "registration"
SPARE_DB = REG_DB / "registered_spares.json"
AUDIT_DB = REG_DB / "registration_audit.json"

REG_DB.mkdir(parents=True, exist_ok=True)

def _load(path, default):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return default

def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

def _audit(action, entity, identifier, details=None):
    rows = _load(AUDIT_DB, [])
    if not isinstance(rows, list):
        rows = []
    rows.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "entity": entity,
        "identifier": identifier,
        "details": details or {},
        "status": "PENDING_VERIFICATION",
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "HUMAN_DECISION_REQUIRED": True
    })
    _save(AUDIT_DB, rows)

def _clean(v):
    return re.sub(r"\s+", " ", str(v or "").strip(" ,.;:")).strip()

def _norm(v):
    return re.sub(r"[^A-Z0-9]", "", _clean(v).upper())

def _extract(pattern, q, flags=re.I):
    m = re.search(pattern, q, flags)
    return _clean(m.group(1)) if m else ""

def _equipment_tag(q):
    # Explicit tag is authoritative.
    tag = _extract(
        r"\btag\s*(?:is|=|:)?\s*([A-Za-z0-9][A-Za-z0-9._/-]*)", q
    )
    if tag:
        return tag

    # "equipment PT-303", "equipment UPS-002"
    tag = _extract(
        r"\bequipment\s+([A-Za-z][A-Za-z0-9._/-]*)", q
    )
    return tag

def _equipment_name(q, tag):
    name = _extract(
        r"\b(?:equipment|name)\s*(?:is|=|:)?\s*([A-Za-z][A-Za-z0-9 ._/-]*?)(?:\s*,|\s+tag\b|\s+area\b|$)",
        q
    )
    if name:
        return name
    return tag

def _area(q):
    return _extract(
        r"\barea\s*(?:is|=|:)?\s*([^,.;]+?)(?:\s*,|\s+description\b|\s+type\b|\s+tag\b|$)",
        q
    )

def _description(q):
    return _extract(
        r"\bdescription\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _type(q):
    return _extract(
        r"\btype\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _manufacturer(q):
    return _extract(
        r"\bmanufacturer\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _model(q):
    return _extract(
        r"\bmodel\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _serial(q):
    return _extract(
        r"\bserial(?:\s+number)?\s*(?:is|=|:)?\s*([A-Za-z0-9._/-]+)",
        q
    )

def _plc(q):
    return _extract(
        r"\bPLC\s*(?:address|addr)?\s*(?:is|=|:)?\s*([A-Za-z0-9._/-]+)",
        q
    )

def _io(q):
    return _extract(
        r"\bI/?O\s*(?:address)?\s*(?:is|=|:)?\s*([A-Za-z0-9._/-]+)",
        q
    )

def _source(q):
    return _extract(
        r"\bsource\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _is_equipment_registration(q):
    x = q.lower()
    registration = any(k in x for k in (
        "add new equipment",
        "register new equipment",
        "register equipment",
        "create new equipment",
        "add equipment",
        "new equipment",
        "add new tag",
        "register new tag",
        "register tag",
        "create equipment identity",
        "create digital identity",
    ))
    # Ordinary questions such as "do we have equipment UPS-2?" must not mutate.
    question = any(k in x for k in (
        "do we have", "show me", "what is", "where is",
        "tell me", "find ", "search "
    ))
    return registration and not question

def _is_new_spare_registration(q):
    x = q.lower()
    registration = any(k in x for k in (
        "register new spare",
        "register a new spare",
        "add new spare item",
        "add a new spare",
        "create new spare",
        "create a new spare",
        "new spare for",
        "register spare for",
    ))
    # Existing stock commands must remain under pci_spares.
    transaction = any(k in x for k in (
        "add 1 ", "add 2 ", "add 3 ", "add 4 ", "add 5 ",
        "add 6 ", "add 7 ", "add 8 ", "add 9 ",
        "add 10 ", "use ", "used ", "consume ",
        "issued ", "issue "
    ))
    return registration and not transaction

def _quantity(q):
    patterns = (
        r"\b(\d+)\s*(?:nos?|pieces?|pcs?|units?)\b",
        r"\bquantity\s*(?:is|=|:)?\s*(\d+)\b",
        r"\bqty\s*(?:is|=|:)?\s*(\d+)\b",
    )
    for p in patterns:
        v = _extract(p, q)
        if v:
            return int(v)
    return 0

def _spare_description(q):
    q = _clean(q)

    # Explicit description has highest priority.
    explicit = _description(q)
    if explicit:
        return explicit

    # Capture the text after the equipment/tag association and quantity,
    # stopping before optional metadata.
    m = re.search(
        r"\bspare\s+for\s+([A-Za-z0-9][A-Za-z0-9._/-]*)"
        r"\s*,\s*\d+\s*(?:nos?|pieces?|pcs?|units?)\s*,\s*"
        r"(.+?)(?=\s*,\s*(?:category|manufacturer|model|location|source)\b|$)",
        q,
        re.I
    )
    if m:
        value=_clean(m.group(2))
        if value:
            return value

    # Fallback: text following the quantity.
    m = re.search(
        r"\b\d+\s*(?:nos?|pieces?|pcs?|units?)\s*,\s*(.+)$",
        q,
        re.I
    )
    if m:
        value=_clean(m.group(1))
        value=re.split(
            r"\s*,\s*(?:category|manufacturer|model|location|source)\b",
            value,
            maxsplit=1,
            flags=re.I
        )[0]
        if value:
            return _clean(value)

    return ""

def _spare_equipment(q):
    # "spare for UPS-2"
    return _extract(
        r"\bspare\s+for\s+([A-Za-z][A-Za-z0-9._/-]*)",
        q
    )

def _spare_category(q):
    return _extract(
        r"\bcategory\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _spare_location(q):
    return _extract(
        r"\blocation\s*(?:is|=|:)?\s*([^,.;]+)",
        q
    )

def _min_qty(q):
    v = _extract(r"\b(?:min(?:imum)?|critical)\s*(?:qty|quantity)?\s*(?:is|=|:)?\s*(\d+)", q)
    return int(v) if v else None

def _equipment_db_lookup(tag):
    try:
        from equipment_database import get_equipment
        return get_equipment(tag)
    except Exception:
        return None



def _neon_sync_equipment(record):
    """Best-effort Neon persistence; JSON remains local fallback."""
    try:
        from anvi_neon_store import neon_enabled, init_neon, upsert_equipment
        if neon_enabled():
            init_neon()
            return bool(upsert_equipment(record))
    except Exception:
        pass
    return False


def _neon_sync_spare(record):
    """Best-effort Neon persistence; JSON remains local fallback."""
    try:
        from anvi_neon_store import neon_enabled, init_neon, upsert_registered_spare
        if neon_enabled():
            init_neon()
            return bool(upsert_registered_spare(record))
    except Exception:
        pass
    return False


def _neon_sync_audit(event):
    """Best-effort Neon audit persistence."""
    try:
        from anvi_neon_store import neon_enabled, init_neon, audit
        if neon_enabled():
            init_neon()
            return bool(audit(event))
    except Exception:
        pass
    return False

def register_equipment(question):
    q = _clean(question)
    tag = _equipment_tag(q)

    if not tag:
        return {
            "ok": False,
            "domain": "equipment_registration",
            "message": "I need the new equipment tag. Example: Add new equipment UPS-2, tag UPS-002, area Main Center Plant."
        }

    existing = _equipment_db_lookup(tag)
    if existing:
        return {
            "ok": False,
            "domain": "equipment_registration",
            "duplicate": True,
            "tag": tag,
            "message": f"Equipment tag {tag} already exists. I did not create a duplicate."
        }

    name = _equipment_name(q, tag)
    area = _area(q)
    description = _description(q)
    eq_type = _type(q)
    manufacturer = _manufacturer(q)
    model = _model(q)
    serial = _serial(q)
    plc = _plc(q)
    io = _io(q)
    source = _source(q)

    record = {
        "tag": tag,
        "name": name,
        "type": eq_type,
        "area": area,
        "location": "",
        "service": description,
        "plc": plc,
        "io_address": io,
        "jb": "",
        "terminal": "",
        "range": "",
        "unit": "",
        "criticality": "MEDIUM",
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial,
        "spare_available": False,
        "spare_quantity": 0,
        "spare_location": "",
        "installation_date": "",
        "expected_life": "",
        "expiry_date": "",
        "maintenance_history": [],
        "calibration_history": [],
        "failure_history": [],

        # ANVIQO registration metadata
        "description": description,
        "hierarchy": {
            "area": area
        },
        "source": source or "CONVERSATIONAL_REGISTRATION",
        "registered_at": datetime.now().isoformat(timespec="seconds"),
        "verification_status": "PENDING_VERIFICATION",
        "registration_status": "PENDING_VERIFICATION",
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "HUMAN_DECISION_REQUIRED": True
    }

    try:
        from equipment_database import add_equipment
        result = add_equipment(record)
        if not result or not result.get("success"):
            return {
                "ok": False,
                "domain": "equipment_registration",
                "message": str((result or {}).get("message", "Equipment registration failed."))
            }
    except Exception as e:
        return {
            "ok": False,
            "domain": "equipment_registration",
            "message": f"Equipment registration failed safely: {e}"
        }

    _audit("REGISTER", "EQUIPMENT", tag, record)

    return {
        "ok": True,
        "domain": "equipment_registration",
        "executed": True,
        "tag": tag,
        "name": name,
        "area": area,
        "verification_status": "PENDING_VERIFICATION",
        "message": (
            f"ANVI registered new equipment {name} [{tag}]. "
            f"Area: {area or 'not supplied'}. "
            f"Status: PENDING_VERIFICATION. "
            f"No PLC/SCADA action was performed."
        )
    }

def register_spare(question):
    q = _clean(question)
    equipment = _spare_equipment(q)
    qty = _quantity(q)
    description = _spare_description(q)
    category = _spare_category(q)
    manufacturer = _manufacturer(q)
    model = _model(q)
    location = _spare_location(q)
    minimum = _min_qty(q)
    source = _source(q)

    if not equipment:
        return {
            "ok": False,
            "domain": "spare_registration",
            "message": "I need the equipment/tag association. Example: Register a new spare for UPS-2, 2 nos, Schneider 24V DC power supply."
        }

    if qty <= 0:
        return {
            "ok": False,
            "domain": "spare_registration",
            "message": "Please provide the new spare quantity, for example 2 nos."
        }

    if not description:
        return {
            "ok": False,
            "domain": "spare_registration",
            "message": "Please provide the spare description."
        }

    rows = _load(SPARE_DB, [])
    if not isinstance(rows, list):
        rows = []

    eid = _norm(equipment)
    # Prevent accidental duplicate registration of identical spare descriptions
    for row in rows:
        if (
            _norm(row.get("equipment_tag")) == eid and
            _norm(row.get("description")) == _norm(description) and
            _norm(row.get("manufacturer")) == _norm(manufacturer) and
            _norm(row.get("model")) == _norm(model)
        ):
            return {
                "ok": False,
                "domain": "spare_registration",
                "duplicate": True,
                "spare_id": row.get("spare_id"),
                "message": (
                    f"This spare is already registered for {equipment} "
                    f"as {row.get('spare_id')}. I did not create a duplicate."
                )
            }

    spare_id = "REG-SP-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

    record = {
        "spare_id": spare_id,
        "equipment_tag": equipment,
        "description": description,
        "category": category,
        "manufacturer": manufacturer,
        "model": model,
        "quantity": qty,
        "location": location,
        "minimum_quantity": minimum,
        "critical_quantity": minimum,
        "source": source or "CONVERSATIONAL_REGISTRATION",
        "registered_at": datetime.now().isoformat(timespec="seconds"),
        "verification_status": "PENDING_VERIFICATION",
        "status": "PENDING_VERIFICATION",
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "HUMAN_DECISION_REQUIRED": True
    }

    rows.append(record)
    _save(SPARE_DB, rows)
    _audit("REGISTER", "SPARE", spare_id, record)

    return {
        "ok": True,
        "domain": "spare_registration",
        "executed": True,
        "spare_id": spare_id,
        "equipment_tag": equipment,
        "quantity": qty,
        "verification_status": "PENDING_VERIFICATION",
        "message": (
            f"ANVI registered new spare {spare_id} for {equipment}: "
            f"{description}, quantity {qty}. "
            f"Status: PENDING_VERIFICATION. "
            f"No PLC/SCADA action was performed."
        )
    }


def answer_registered_query(question):
    """
    Read-only retrieval of conversationally registered equipment/spares.

    This route exists separately from the legacy PCI Critical Spare engine.
    Registered records remain PENDING_VERIFICATION and never authorize
    PLC/SCADA action.
    """
    q = _clean(question)
    ql = q.lower()

    spare_intent = any(term in ql for term in (
        "spare", "spares", "spare available",
        "available spare", "available spares",
        "do we have a spare", "do we have spares",
        "show me spares", "spare for"
    ))

    if not spare_intent:
        return None

    # Resolve an explicit equipment/tag reference.
    candidates = []

    m = re.search(
        r"\b(?:spare|spares)\s+for\s+([A-Za-z0-9][A-Za-z0-9._/-]*)",
        q,
        re.I
    )
    if m:
        candidates.append(_clean(m.group(1)))

    m = re.search(
        r"\b(?:equipment|tag)\s+([A-Za-z0-9][A-Za-z0-9._/-]*)",
        q,
        re.I
    )
    if m:
        candidates.append(_clean(m.group(1)))

    # Also recognise "Do we have spares for MT-401?"
    m = re.search(
        r"\b(?:for|of)\s+([A-Za-z][A-Za-z0-9._/-]*)\s*\??$",
        q,
        re.I
    )
    if m:
        candidates.append(_clean(m.group(1)))

    candidates = [x for x in candidates if x]
    if not candidates:
        return None

    tag = candidates[0]
    tag_norm = _norm(tag)

    rows = _load(SPARE_DB, [])
    if not isinstance(rows, list):
        rows = []

    matches = [
        row for row in rows
        if isinstance(row, dict)
        and _norm(row.get("equipment_tag")) == tag_norm
    ]

    # Only take over routing when this is actually a registered equipment
    # or registered spare. Otherwise the existing PCI/Critical Spare engine
    # remains authoritative.
    equipment = _equipment_db_lookup(tag)

    if not matches and not equipment:
        return None

    if matches:
        lines = [
            f"ANVI found {len(matches)} registered spare record(s) for {tag}.",
            "Source: ANVI Conversational Registration.",
        ]

        for row in matches:
            lines.append(
                f"{row.get('spare_id', 'UNNAMED')} — "
                f"{row.get('description', 'Spare item')}; "
                f"Quantity: {row.get('quantity', 0)}; "
                f"Location: {row.get('location') or 'not recorded'}; "
                f"Status: {row.get('verification_status') or row.get('status') or 'PENDING_VERIFICATION'}."
            )

        lines.append(
            "These registered spare records are PENDING_VERIFICATION. "
            "They are historical/registration evidence only and do not authorize "
            "PLC/SCADA action. Human verification remains required."
        )

        return {
            "ok": True,
            "domain": "spare_registration",
            "registered_spare_query": True,
            "equipment_tag": tag,
            "records": matches,
            "count": len(matches),
            "answer": "\n".join(lines),
            "read_only": True,
            "PLC_WRITE": False,
            "SCADA_CONTROL": False,
            "human_decision_required": True,
        }

    # Equipment exists as a conversational registration, but no registered
    # spare is currently associated with it.
    return {
        "ok": True,
        "domain": "spare_registration",
        "registered_spare_query": True,
        "equipment_tag": tag,
        "records": [],
        "count": 0,
        "answer": (
            f"ANVI found registered equipment {tag}, but no "
            f"conversationally registered spare is currently associated with {tag}. "
            f"Status of the equipment registration: "
            f"{equipment.get('verification_status', 'PENDING_VERIFICATION')}. "
            "This does not prove that no physical/store spare exists; "
            "the registered-spare database contains no matching record. "
            "No PLC/SCADA action was performed."
        ),
        "read_only": True,
        "PLC_WRITE": False,
        "SCADA_CONTROL": False,
        "human_decision_required": True,
    }

def answer_registration(question):
    q = _clean(question)

    if _is_equipment_registration(q):
        return register_equipment(q)

    if _is_new_spare_registration(q):
        return register_spare(q)

    return None

def registration_answer_text(result):
    if not result:
        return ""
    return str(result.get("message", "")).strip()
