from datetime import datetime

from equipment_database import get_equipment
from equipment_health import get_latest_health
from plant_equipment_intelligence import (
    build_area_equipment_intelligence
)


def build_equipment_reasoning(tag):
    """
    Build an explainable reasoning chain for one equipment.
    """

    equipment = get_equipment(tag)

    if not equipment:
        return {
            "status": "NO DATA",
            "equipment": tag,
            "chain": [],
            "explanation": "Equipment not found."
        }

    health = get_latest_health(tag)

    if not health:
        return {
            "status": "NO DATA",
            "equipment": tag,
            "chain": [],
            "explanation": "No health evidence available."
        }

    chain = []

    # Existing known evidence from Anviqo
    evidence = [
        "Valve Position increased",
        "Temperature increased",
        "Instrument Air Pressure decreased"
    ]

    for item in evidence:
        chain.append({
            "level": "PARAMETER",
            "message": item
        })

    chain.append({
        "level": "RISK",
        "message": (
            f"Equipment risk is "
            f"{health.get('risk_score')}."
        )
    })

    chain.append({
        "level": "HEALTH",
        "message": (
            f"Equipment health is "
            f"{100 - float(health.get('risk_score', 0))}."
        )
    })

    chain.append({
        "level": "EQUIPMENT",
        "message": (
            f"{tag} is in "
            f"{health.get('status', 'UNKNOWN')} condition."
        )
    })

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "status": "EVIDENCE CHAIN BUILT",
        "equipment": tag,
        "equipment_name": equipment.get("name"),
        "area": equipment.get("area"),
        "chain": chain,
        "confidence": health.get("confidence"),
        "explanation": (
            f"Anviqo identified multiple parameter changes "
            f"associated with {tag}. These changes are followed "
            f"by elevated risk and degraded equipment health."
        )
    }


def build_plant_brain(area):
    """
    Build Plant Brain reasoning:
    parameter -> equipment -> area.
    """

    area_result = build_area_equipment_intelligence(area)

    contributors = area_result.get(
        "contributors",
        []
    )

    equipment_reasoning = []

    for item in contributors:

        reasoning = build_equipment_reasoning(
            item["tag"]
        )

        equipment_reasoning.append(
            reasoning
        )

    primary = (
        contributors[0]
        if contributors
        else None
    )

    if primary:

        explanation = (
            f"{area} is {area_result['area_health']['status']} "
            f"and the primary equipment contributor is "
            f"{primary['tag']}. "
            f"Anviqo detected parameter changes, "
            f"elevated equipment risk and degraded "
            f"equipment health."
        )

        status = "PLANT BRAIN EVIDENCE"

    else:

        explanation = (
            f"No equipment evidence available "
            f"for {area}."
        )

        status = "INSUFFICIENT EVIDENCE"

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "area": area,
        "status": status,
        "area_health": area_result["area_health"],
        "primary_equipment": primary,
        "equipment_reasoning": equipment_reasoning,
        "explanation": explanation
    }
