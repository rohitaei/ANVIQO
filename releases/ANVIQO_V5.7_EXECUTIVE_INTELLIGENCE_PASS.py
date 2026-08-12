"""
ANVIQO V5.7
EXECUTIVE / HOD INTELLIGENCE

Purpose:
    Consolidate existing ANVIQO intelligence into one
    management-facing executive view.

Important:
    - Read-only
    - No PLC write
    - No SCADA write
    - No automatic authorization
    - No automatic execution
    - Does not establish causation
    - Does not duplicate existing intelligence engines
"""

from datetime import datetime


VERSION = "V5.7"


def build_executive_intelligence(
    plant_status=None,
    plant_health=None,
    what_changed=None,
    equipment_risks=None,
    event_chains=None,
    decisions=None,
    shift_summary=None,
):
    plant_status = plant_status or {}
    plant_health = plant_health or {}
    what_changed = what_changed or {}
    equipment_risks = equipment_risks or []
    event_chains = event_chains or []
    decisions = decisions or []
    shift_summary = shift_summary or {}

    # ---------------------------------------------------------
    # PLANT SITUATION
    # ---------------------------------------------------------

    situation = plant_status.get(
        "status",
        plant_status.get(
            "overall_status",
            "NO DATA"
        )
    )

    # ---------------------------------------------------------
    # PLANT HEALTH
    # ---------------------------------------------------------

    health_status = plant_health.get(
        "status",
        plant_health.get(
            "overall_status",
            "NO DATA"
        )
    )

    health_score = plant_health.get(
        "score",
        plant_health.get(
            "health_score",
            None
        )
    )

    # ---------------------------------------------------------
    # TOP EQUIPMENT RISKS
    # ---------------------------------------------------------

    normalized_risks = []

    if isinstance(equipment_risks, dict):
        equipment_risks = (
            equipment_risks.get("ranking")
            or equipment_risks.get("equipment")
            or []
        )

    for item in equipment_risks:
        if not isinstance(item, dict):
            continue

        normalized_risks.append({
            "equipment": item.get(
                "equipment",
                item.get("tag", "UNKNOWN")
            ),
            "priority": item.get(
                "priority",
                item.get("priority_score", 0)
            ),
            "status": item.get(
                "status",
                item.get("severity", "UNKNOWN")
            ),
            "reason": item.get(
                "reason",
                item.get("message", "")
            ),
        })

    normalized_risks.sort(
        key=lambda x: float(x.get("priority", 0) or 0),
        reverse=True
    )

    # ---------------------------------------------------------
    # WHAT CHANGED
    # ---------------------------------------------------------

    changes = []

    if isinstance(what_changed, dict):
        changes = (
            what_changed.get("changes")
            or what_changed.get("parameters")
            or what_changed.get("events")
            or []
        )

    elif isinstance(what_changed, list):
        changes = what_changed

    # ---------------------------------------------------------
    # EVENT CHAINS
    # ---------------------------------------------------------

    normalized_chains = []

    for chain in event_chains:
        if not isinstance(chain, dict):
            continue

        normalized_chains.append({
            "equipment": chain.get(
                "equipment",
                chain.get("equipment_pair", "UNKNOWN")
            ),
            "status": chain.get(
                "status",
                "DEVELOPING EVENT CHAIN"
            ),
            "evidence": chain.get(
                "evidence",
                chain.get("chain", [])
            ),
            "causation_established": False,
        })

    # ---------------------------------------------------------
    # DECISION QUEUE
    # ---------------------------------------------------------

    decision_queue = []

    for decision in decisions:
        if not isinstance(decision, dict):
            continue

        decision_queue.append({
            "equipment": decision.get(
                "equipment",
                "UNKNOWN"
            ),
            "priority": decision.get(
                "priority",
                decision.get("maintenance_priority", 0)
            ),
            "decision": decision.get(
                "decision",
                "REVIEW REQUIRED"
            ),
            "recommendation": decision.get(
                "recommendation",
                decision.get(
                    "recommended_action",
                    ""
                )
            ),
            "human_required": True,
        })

    decision_queue.sort(
        key=lambda x: float(x.get("priority", 0) or 0),
        reverse=True
    )

    # ---------------------------------------------------------
    # EXECUTIVE PRIORITY
    # ---------------------------------------------------------

    if normalized_risks:
        top_priority = float(
            normalized_risks[0].get("priority", 0) or 0
        )
    elif decision_queue:
        top_priority = float(
            decision_queue[0].get("priority", 0) or 0
        )
    else:
        top_priority = 0

    if top_priority >= 80:
        management_priority = "P1 — URGENT"
    elif top_priority >= 60:
        management_priority = "P2 — HIGH"
    elif top_priority >= 50:
        management_priority = "P3 — MONITOR"
    else:
        management_priority = "NORMAL"

    # ---------------------------------------------------------
    # MANAGEMENT MESSAGE
    # ---------------------------------------------------------

    if normalized_risks:
        top = normalized_risks[0]

        management_message = (
            f"Primary management concern is "
            f"{top['equipment']} with priority "
            f"{top['priority']}/100. "
            f"{top['reason']}"
        )

    elif decision_queue:
        top = decision_queue[0]

        management_message = (
            f"Management review is required for "
            f"{top['equipment']}."
        )

    else:
        management_message = (
            "No high-priority management concern "
            "was identified from the supplied evidence."
        )

    # ---------------------------------------------------------
    # SAFETY / GOVERNANCE
    # ---------------------------------------------------------

    safety_boundary = {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
        "automatic_authorization": False,
        "automatic_execution": False,
        "causation_claim": False,
    }

    # ---------------------------------------------------------
    # FINAL EXECUTIVE OBJECT
    # ---------------------------------------------------------

    return {
        "version": VERSION,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),

        "executive_status": "MANAGEMENT REVIEW",

        "plant_situation": situation,

        "plant_health": {
            "status": health_status,
            "score": health_score,
        },

        "management_priority": management_priority,

        "top_equipment_risks": normalized_risks[:5],

        "what_changed": changes[:10],

        "developing_event_chains": normalized_chains[:10],

        "decision_queue": decision_queue[:10],

        "shift_summary": shift_summary,

        "management_message": management_message,

        "evidence_available": bool(
            normalized_risks
            or changes
            or normalized_chains
            or decision_queue
        ),

        "uncertainty": {
            "causation_established": False,
            "requires_human_review": True,
        },

        "safety_boundary": safety_boundary,
    }


def print_executive_intelligence(result):

    print()
    print("=" * 72)
    print("        ANVIQO V5.7 EXECUTIVE INTELLIGENCE")
    print("=" * 72)

    print()
    print("EXECUTIVE STATUS")
    print("-" * 72)
    print(result["executive_status"])

    print()
    print("PLANT SITUATION")
    print("-" * 72)
    print(result["plant_situation"])

    print()
    print("PLANT HEALTH")
    print("-" * 72)

    health = result["plant_health"]

    print("Status :", health["status"])
    print("Score  :", health["score"])

    print()
    print("MANAGEMENT PRIORITY")
    print("-" * 72)
    print(result["management_priority"])

    print()
    print("TOP EQUIPMENT RISKS")
    print("-" * 72)

    if result["top_equipment_risks"]:
        for item in result["top_equipment_risks"]:
            print(
                f'✓ {item["equipment"]} | '
                f'Priority {item["priority"]}/100 | '
                f'{item["status"]}'
            )
            if item["reason"]:
                print("  ", item["reason"])
    else:
        print("No equipment risk data.")

    print()
    print("WHAT CHANGED")
    print("-" * 72)

    if result["what_changed"]:
        for change in result["what_changed"]:
            print("✓", change)
    else:
        print("No change data supplied.")

    print()
    print("DEVELOPING EVENT CHAINS")
    print("-" * 72)

    if result["developing_event_chains"]:
        for chain in result["developing_event_chains"]:
            print(
                f'✓ {chain["equipment"]} | '
                f'{chain["status"]}'
            )
            print(
                "  Causation established :",
                chain["causation_established"]
            )
    else:
        print("No developing event chains.")

    print()
    print("DECISION QUEUE")
    print("-" * 72)

    if result["decision_queue"]:
        for decision in result["decision_queue"]:
            print(
                f'✓ {decision["equipment"]} | '
                f'Priority {decision["priority"]}/100 | '
                f'{decision["decision"]}'
            )
            print(
                "  Recommendation :",
                decision["recommendation"]
            )
    else:
        print("No pending decisions.")

    print()
    print("MANAGEMENT MESSAGE")
    print("-" * 72)
    print(result["management_message"])

    print()
    print("EVIDENCE / UNCERTAINTY")
    print("-" * 72)
    print(
        "Evidence available :",
        result["evidence_available"]
    )
    print(
        "Causation established :",
        result["uncertainty"]["causation_established"]
    )
    print(
        "Human review required :",
        result["uncertainty"]["requires_human_review"]
    )

    print()
    print("SAFETY / CONTROL BOUNDARY")
    print("-" * 72)

    safety = result["safety_boundary"]

    print(
        "READ-ONLY               :",
        str(safety["read_only"]).upper()
    )
    print(
        "PLC WRITE               :",
        str(safety["plc_write"]).upper()
    )
    print(
        "SCADA CONTROL           :",
        str(safety["scada_control"]).upper()
    )
    print(
        "HUMAN DECISION REQUIRED :",
        str(safety["human_decision_required"]).upper()
    )
    print(
        "AUTOMATIC AUTHORIZATION :",
        str(safety["automatic_authorization"]).upper()
    )
    print(
        "AUTOMATIC EXECUTION     :",
        str(safety["automatic_execution"]).upper()
    )
    print(
        "CAUSATION CLAIM         :",
        str(safety["causation_claim"]).upper()
    )

    print()
    print("=" * 72)


def run_v57_test():

    sample = build_executive_intelligence(
        plant_status={
            "status": "ATTENTION REQUIRED"
        },

        plant_health={
            "status": "DEGRADED",
            "health_score": 72.4
        },

        what_changed={
            "changes": [
                "CV-101 valve position increased significantly.",
                "CV-102 valve position is in warning condition.",
                "PT-201 pressure requires attention."
            ]
        },

        equipment_risks=[
            {
                "equipment": "CV-101",
                "priority_score": 84.7,
                "severity": "URGENT",
                "reason":
                    "Valve position is increasing significantly."
            },
            {
                "equipment": "CV-102",
                "priority_score": 71.2,
                "severity": "HIGH",
                "reason":
                    "Valve position warning with related event activity."
            },
            {
                "equipment": "PT-201",
                "priority_score": 63.5,
                "severity": "ATTENTION",
                "reason":
                    "Pressure condition requires investigation."
            }
        ],

        event_chains=[
            {
                "equipment_pair": "CV-101 ↔ CV-102",
                "status": "DEVELOPING EVENT CHAIN",
                "evidence": [
                    "Relationship: PROCESS_RELATED",
                    "Related event activity detected."
                ]
            },
            {
                "equipment_pair": "CV-102 ↔ PT-201",
                "status": "DEVELOPING EVENT CHAIN",
                "evidence": [
                    "Relationship: PROCESS_RELATED",
                    "Chronological event activity detected."
                ]
            }
        ],

        decisions=[
            {
                "equipment": "CV-101",
                "priority": 84.7,
                "decision":
                    "MAINTENANCE REVIEW REQUIRED",
                "recommendation":
                    "Perform controlled maintenance review."
            }
        ],

        shift_summary={
            "status": "SHIFT REVIEW REQUIRED"
        }
    )

    print_executive_intelligence(sample)

    safety = sample["safety_boundary"]

    passed = (
        sample["version"] == "V5.7"
        and sample["evidence_available"] is True
        and sample["management_priority"] == "P1 — URGENT"
        and safety["read_only"] is True
        and safety["plc_write"] is False
        and safety["scada_control"] is False
        and safety["human_decision_required"] is True
        and safety["automatic_authorization"] is False
        and safety["automatic_execution"] is False
        and safety["causation_claim"] is False
    )

    print()
    print("=" * 72)

    if passed:
        print("V5.7 MODULE TEST: PASS")
        print("EXECUTIVE / HOD INTELLIGENCE: PASS")
        print("EVIDENCE CONSOLIDATION: PASS")
        print("MANAGEMENT PRIORITY: PASS")
        print("HUMAN GOVERNANCE: PASS")
        print("SAFETY BOUNDARY: PASS")
    else:
        print("V5.7 MODULE TEST: FAIL")

    print("=" * 72)

    return passed


if __name__ == "__main__":
    run_v57_test()
