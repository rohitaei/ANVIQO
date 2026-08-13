from datetime import datetime

from advanced_what_changed import generate_advanced_what_changed
from event_correlation import correlate_events
from plant_health_intelligence import build_plant_health_intelligence


def build_plant_what_changed(
    plant_name,
    area_results,
    equipment_events=None
):
    """
    ANVIQO V5.0.7
    Plant-level What Changed intelligence.

    Combines:
    - Plant health intelligence
    - Equipment reasoning
    - Event correlation
    - Evidence chain

    Read-only analysis.
    """

    equipment_events = equipment_events or []

    if not area_results:
        return {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "plant": plant_name,
            "status": "NO DATA",
            "health_score": None,
            "areas": [],
            "primary_area": None,
            "primary_equipment": None,
            "reasoning_chain": [],
            "correlations": [],
            "explanation": "No plant health data available.",
            "evidence": {
                "available": False,
                "confidence": 0
            }
        }

    # ---------------------------------
    # Plant health intelligence
    # ---------------------------------

    plant_intelligence = build_plant_health_intelligence(
        plant_name,
        area_results
    )

    # ---------------------------------
    # Find most critical area
    # ---------------------------------

    valid_areas = [
        area for area in area_results
        if area.get("health_score") is not None
    ]

    valid_areas.sort(
        key=lambda x: float(
            x.get("health_score", 100)
        )
    )

    primary_area = (
        valid_areas[0]
        if valid_areas
        else None
    )

    # ---------------------------------
    # Find primary equipment
    # ---------------------------------

    primary_equipment = None

    if primary_area:

        contributors = primary_area.get(
            "equipment",
            []
        )

        if contributors:
            primary_equipment = sorted(
                contributors,
                key=lambda x: float(
                    x.get("risk_score", 0)
                ),
                reverse=True
            )[0]

    # ---------------------------------
    # Reasoning chain
    # ---------------------------------

    reasoning_chain = []

    if primary_area:

        reasoning_chain.append(
            f"[AREA] {primary_area.get('area')} "
            f"is {primary_area.get('status')}."
        )

    if primary_equipment:

        tag = primary_equipment.get(
            "tag",
            "UNKNOWN"
        )

        name = primary_equipment.get(
            "name",
            "Equipment"
        )

        risk = primary_equipment.get(
            "risk_score",
            "UNKNOWN"
        )

        health = primary_equipment.get(
            "health_score",
            "UNKNOWN"
        )

        reasoning_chain.append(
            f"[EQUIPMENT] {tag} ({name}) "
            f"risk={risk}, health={health}."
        )

    # ---------------------------------
    # Correlate equipment events
    # ---------------------------------

    correlations = []

    if primary_equipment:

        tag = primary_equipment.get(
            "tag"
        )

        events = equipment_events.get(
            tag,
            []
        ) if isinstance(
            equipment_events,
            dict
        ) else equipment_events

        if events:

            correlation = correlate_events(
                tag,
                events
            )

            correlations.append(
                correlation
            )

            for item in correlation.get(
                "chain",
                []
            ):

                reasoning_chain.append(
                    f"[CORRELATION] {item}"
                )

    # ---------------------------------
    # Add plant intelligence
    # ---------------------------------

    contributors = plant_intelligence.get(
        "contributors",
        []
    )

    for contributor in contributors:

        reasoning_chain.append(
            f"[PLANT] {contributor.get('area')} "
            f"area contribution: "
            f"{contributor.get('status')}."
        )

    # ---------------------------------
    # Determine confidence
    # ---------------------------------

    evidence_count = 0

    if primary_area:
        evidence_count += 1

    if primary_equipment:
        evidence_count += 1

    if correlations:
        evidence_count += 1

    if contributors:
        evidence_count += 1

    confidence_map = {
        0: 20,
        1: 40,
        2: 60,
        3: 80,
        4: 90
    }

    confidence = confidence_map.get(
        min(evidence_count, 4),
        90
    )

    # ---------------------------------
    # Explanation
    # ---------------------------------

    if primary_area and primary_equipment:

        explanation = (
            f"{primary_area.get('area')} is "
            f"{primary_area.get('status')} and is "
            f"the primary affected area. "
            f"The main equipment contributor is "
            f"{primary_equipment.get('tag')} "
            f"({primary_equipment.get('name')}). "
            f"Anviqo combined plant health, "
            f"equipment condition and available "
            f"event evidence to identify this condition."
        )

    elif primary_area:

        explanation = (
            f"{primary_area.get('area')} is the "
            f"primary affected area based on "
            f"available plant health data."
        )

    else:

        explanation = (
            "Plant condition detected, but "
            "insufficient information is available "
            "to identify the primary contributor."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "plant": plant_name,
        "status": plant_intelligence.get(
            "status",
            "UNKNOWN"
        ),
        "health_score": plant_intelligence.get(
            "health_score"
        ),
        "areas": area_results,
        "primary_area": primary_area,
        "primary_equipment": primary_equipment,
        "reasoning_chain": reasoning_chain,
        "correlations": correlations,
        "explanation": explanation,
        "evidence": {
            "available": evidence_count > 0,
            "evidence_count": evidence_count,
            "confidence": confidence
        }
    }
