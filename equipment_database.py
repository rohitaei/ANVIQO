import json
import os

DB_FILE = os.path.join("database", "equipment.json")


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f, indent=4)


def load_equipment():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def save_equipment(data):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_equipment(equipment):
    data = load_equipment()

    tag = equipment.get("tag", "").strip()

    if not tag:
        return {
            "success": False,
            "message": "Equipment tag is required."
        }

    for item in data:
        if item.get("tag") == tag:
            return {
                "success": False,
                "message": f"Equipment {tag} already exists."
            }

    equipment.setdefault("name", "")
    equipment.setdefault("type", "")
    equipment.setdefault("area", "")
    equipment.setdefault("location", "")
    equipment.setdefault("service", "")

    equipment.setdefault("plc", "")
    equipment.setdefault("io_address", "")
    equipment.setdefault("jb", "")
    equipment.setdefault("terminal", "")

    equipment.setdefault("range", "")
    equipment.setdefault("unit", "")

    equipment.setdefault("criticality", "MEDIUM")

    equipment.setdefault("manufacturer", "")
    equipment.setdefault("model", "")
    equipment.setdefault("serial_number", "")

    equipment.setdefault("spare_available", False)
    equipment.setdefault("spare_quantity", 0)
    equipment.setdefault("spare_location", "")

    equipment.setdefault("installation_date", "")
    equipment.setdefault("expected_life", "")
    equipment.setdefault("expiry_date", "")

    equipment.setdefault("maintenance_history", [])
    equipment.setdefault("calibration_history", [])
    equipment.setdefault("failure_history", [])

    data.append(equipment)

    save_equipment(data)

    return {
        "success": True,
        "message": f"Equipment {tag} registered successfully.",
        "equipment": equipment
    }


def get_equipment(tag=None):

    data = load_equipment()

    if tag:
        for item in data:
            if item.get("tag") == tag:
                return item

        return None

    return data


def update_equipment(tag, updates):

    data = load_equipment()

    for item in data:

        if item.get("tag") == tag:

            item.update(updates)

            save_equipment(data)

            return {
                "success": True,
                "message": f"Equipment {tag} updated successfully.",
                "equipment": item
            }

    return {
        "success": False,
        "message": f"Equipment {tag} not found."
    }


def delete_equipment(tag):

    data = load_equipment()

    new_data = [
        item for item in data
        if item.get("tag") != tag
    ]

    if len(new_data) == len(data):

        return {
            "success": False,
            "message": f"Equipment {tag} not found."
        }

    save_equipment(new_data)

    return {
        "success": True,
        "message": f"Equipment {tag} deleted."
    }
