from datetime import datetime

from equipment_database import get_equipment
from equipment_health import get_latest_health
from plant_equipment_intelligence import build_area_equipment_intelligence


def _memory_evidence(tag):
    """Return persistent Plant Memory evidence without mutating memory."""
    try:
        import plant_memory
        records = plant_memory.search_all_memory(query="", tag=tag, limit=50)
    except Exception:
        return []

    evidence = []
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("source") != "technician field report":
            continue
        verified = bool(record.get("verified")) or str(record.get("verification_status", "")).upper() == "VERIFIED"
        if not verified:
            continue
        evidence.append({
            "memory_id": record.get("memory_id"),
            "timestamp": record.get("timestamp") or record.get("created_at"),
            "source": record.get("source"),
            "event": record.get("event"),
            "finding": record.get("finding"),
            "maintenance_action": record.get("maintenance_action"),
            "outcome": record.get("outcome"),
            "spare_used": record.get("spare_used"),
        })
    return evidence


def build_equipment_reasoning(tag):
    """Build an evidence-backed reasoning chain for one equipment."""
    equipment = get_equipment(tag)
    if not equipment:
        return {"status": "NO DATA", "equipment": tag, "chain": [], "explanation": "Equipment not found."}

    health = get_latest_health(tag)
    if not health:
        return {"status": "NO DATA", "equipment": tag, "chain": [], "explanation": "No health evidence available."}

    chain = []
    memory = _memory_evidence(tag)
    for record in memory:
        summary = " | ".join(str(record.get(k) or "").strip() for k in ("event", "finding", "maintenance_action", "outcome") if str(record.get(k) or "").strip())
        if summary:
            chain.append({"level": "MEMORY", "message": summary, "memory_id": record.get("memory_id"), "verified": True})

    chain.append({"level": "RISK", "message": f"Equipment risk is {health.get('risk_score')}."})
    try:
        health_score = 100 - float(health.get("risk_score", 0))
    except (TypeError, ValueError):
        health_score = None
    chain.append({"level": "HEALTH", "message": f"Equipment health is {health_score}." if health_score is not None else "Equipment health score is unavailable."})
    chain.append({"level": "EQUIPMENT", "message": f"{tag} is in {health.get('status', 'UNKNOWN')} condition."})

    if memory:
        explanation = f"ANVIQO combined current equipment health with {len(memory)} verified Plant Memory record(s)."
        status = "EVIDENCE CHAIN BUILT"
    else:
        explanation = "ANVIQO has current equipment health evidence but no verified Plant Memory record for this equipment. No unsupported parameter changes were inferred."
        status = "LIMITED EVIDENCE"

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "equipment": tag,
        "equipment_name": equipment.get("name"),
        "area": equipment.get("area"),
        "chain": chain,
        "confidence": health.get("confidence"),
        "memory_evidence": memory,
        "explanation": explanation,
    }


def build_plant_brain(area):
    """Build Plant Brain using existing V5 equipment intelligence plus verified Plant Memory."""
    area_result = build_area_equipment_intelligence(area)
    contributors = area_result.get("contributors", [])
    equipment_reasoning = [build_equipment_reasoning(item["tag"]) for item in contributors if isinstance(item, dict) and item.get("tag")]
    primary = contributors[0] if contributors else None

    if primary:
        explanation = f"{area} is {area_result['area_health']['status']} and the primary equipment contributor is {primary['tag']}. ANVIQO combines existing equipment/health intelligence with verified Plant Memory where available."
        status = "PLANT BRAIN EVIDENCE"
    else:
        explanation = f"No equipment evidence available for {area}."
        status = "INSUFFICIENT EVIDENCE"

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "area": area,
        "status": status,
        "area_health": area_result["area_health"],
        "primary_equipment": primary,
        "equipment_reasoning": equipment_reasoning,
        "explanation": explanation,
    }
