import json
import os
from datetime import datetime

DB_FILE = os.path.join("database", "equipment_health.json")


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f, indent=4)


def load_health_history():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        return {}


def save_health_history(data):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def record_health(tag, health_result):
    """
    Store one Anvi health observation for an equipment tag.
    """

    if not tag:
        return {
            "success": False,
            "message": "Equipment tag is required."
        }

    data = load_health_history()

    if tag not in data:
        data[tag] = []

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": health_result.get("status", "UNKNOWN"),
        "priority": health_result.get("priority", "UNKNOWN"),
        "risk_score": health_result.get("risk_score", 0),
        "confidence": health_result.get("confidence", 0)
    }

    data[tag].append(entry)

    save_health_history(data)

    return {
        "success": True,
        "message": f"Health observation recorded for {tag}.",
        "entry": entry
    }


def get_health_history(tag):
    data = load_health_history()

    return data.get(tag, [])


def get_latest_health(tag):
    history = get_health_history(tag)

    if not history:
        return None

    return history[-1]


def calculate_health_trend(tag):
    """
    Determine whether equipment health is improving,
    stable or deteriorating based on risk score history.
    """

    history = get_health_history(tag)

    if len(history) < 2:
        return {
            "status": "INSUFFICIENT DATA",
            "message": "At least two health observations are required."
        }

    first = history[0].get("risk_score", 0)
    last = history[-1].get("risk_score", 0)

    change = last - first

    if change >= 15:
        status = "DETERIORATING"
        message = (
            f"{tag} risk has increased by {change} points."
        )

    elif change <= -15:
        status = "IMPROVING"
        message = (
            f"{tag} risk has decreased by {abs(change)} points."
        )

    else:
        status = "STABLE"
        message = (
            f"{tag} risk remains relatively stable."
        )

    return {
        "status": status,
        "first_risk": first,
        "last_risk": last,
        "change": change,
        "message": message
    }
