import json
import os

DB_FILE = os.path.join(
    "database",
    "equipment_relationships.json"
)


def load_relationships():
    if not os.path.exists(DB_FILE):
        return {}

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError):
        return {}


def save_relationships(data):
    os.makedirs(
        os.path.dirname(DB_FILE),
        exist_ok=True
    )

    with open(DB_FILE, "w") as f:
        json.dump(
            data,
            f,
            indent=4
        )


def add_relationship(
    equipment,
    relationship_type,
    target,
    target_type=None
):
    data = load_relationships()

    equipment_data = data.setdefault(
        equipment,
        []
    )

    relationship = {
        "relationship_type": relationship_type,
        "target": target
    }

    if target_type:
        relationship["target_type"] = target_type

    # Prevent duplicate relationships
    if relationship not in equipment_data:
        equipment_data.append(
            relationship
        )

    save_relationships(data)

    return relationship


def get_relationships(equipment):
    data = load_relationships()

    return data.get(
        equipment,
        []
    )


def build_equipment_relationships(
    equipment
):
    relationships = get_relationships(
        equipment
    )

    grouped = {}

    for relationship in relationships:

        relationship_type = relationship.get(
            "relationship_type",
            "RELATED"
        )

        grouped.setdefault(
            relationship_type,
            []
        )

        grouped[relationship_type].append(
            relationship
        )

    return {
        "equipment": equipment,
        "relationship_count": len(
            relationships
        ),
        "relationships": relationships,
        "by_type": grouped
    }
