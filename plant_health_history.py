import json
import os
from datetime import datetime

DB_FILE = os.path.join("database", "plant_health_history.json")


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f, indent=4)


def load_history():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        return {}


def save_history(data):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def record_plant_health(
    plant_name,
    health_score,
    status,
    details=None
):
    """
    Store one plant-health snapshot.
    """

    if not plant_name:
        return {
            "success": False,
            "message": "Plant name is required."
        }

    try:
        score = float(health_score)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Health score must be numeric."
        }

    score = max(0, min(100, score))

    data = load_history()

    if plant_name not in data:
        data[plant_name] = []

    record = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "health_score": round(score, 2),
        "status": status,
        "details": details or {}
    }

    data[plant_name].append(record)

    save_history(data)

    return {
        "success": True,
        "message": (
            f"Plant health recorded for {plant_name}."
        ),
        "record": record
    }


def get_plant_history(plant_name):
    data = load_history()

    return data.get(plant_name, [])


def get_latest_plant_health(plant_name):
    history = get_plant_history(plant_name)

    if not history:
        return None

    return history[-1]


def calculate_health_change(plant_name):
    """
    Compare the first and latest recorded health values.
    """

    history = get_plant_history(plant_name)

    if len(history) < 2:
        return {
            "status": "INSUFFICIENT DATA",
            "message": (
                "At least two health records "
                "are required."
            )
        }

    first = history[0]["health_score"]
    last = history[-1]["health_score"]

    change = round(last - first, 2)

    if change > 0:
        trend = "IMPROVING"

    elif change < 0:
        trend = "DETERIORATING"

    else:
        trend = "STABLE"

    return {
        "first_health": first,
        "last_health": last,
        "change": change,
        "trend": trend,
        "message": (
            f"Plant health changed by {change} points."
        )
    }


def get_health_summary(plant_name):
    history = get_plant_history(plant_name)

    if not history:
        return {
            "plant": plant_name,
            "records": 0,
            "status": "NO DATA"
        }

    latest = history[-1]

    return {
        "plant": plant_name,
        "records": len(history),
        "latest_health": latest["health_score"],
        "latest_status": latest["status"],
        "latest_timestamp": latest["timestamp"]
    }
