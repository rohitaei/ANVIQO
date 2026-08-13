from digital_equipment_identity import (
    build_digital_identity
)

from equipment_relationships import (
    build_equipment_relationships
)


def build_digital_twin(equipment_tag):
    """
    ANVIQO V5.0.3

    Combines:
        V5.0.1 Digital Equipment Identity
        V5.0.2 Equipment Relationships
        Existing V4.11 intelligence

    The twin is a read-only intelligence view.
    It does not modify the underlying databases.
    """

    identity = build_digital_identity(
        equipment_tag
    )

    if identity.get("status") == "NOT FOUND":
        return {
            "equipment": equipment_tag,
            "status": "NOT FOUND"
        }

    relationships = build_equipment_relationships(
        equipment_tag
    )

    intelligence = identity.get(
        "intelligence",
        {}
    )

    health = intelligence.get(
        "health",
        {}
    )

    health_trend = intelligence.get(
        "health_trend",
        {}
    )

    evidence = intelligence.get(
        "evidence",
        {}
    )

    return {
        "status": "ACTIVE",
        "equipment": equipment_tag,

        "identity": identity.get(
            "identity",
            {}
        ),

        "plant": identity.get(
            "plant",
            {}
        ),

        "automation": identity.get(
            "automation",
            {}
        ),

        "technical": identity.get(
            "technical",
            {}
        ),

        "lifecycle": identity.get(
            "lifecycle",
            {}
        ),

        "spares": identity.get(
            "spares",
            {}
        ),

        "relationships": relationships,

        "intelligence": {
            "health": health,
            "health_trend": health_trend,
            "event_count": intelligence.get(
                "event_count",
                0
            ),
            "evidence": evidence
        }
    }
