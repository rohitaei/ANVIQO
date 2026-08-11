import json
import os
from datetime import datetime

DB_FILE = os.path.join(
    "database",
    "event_timeline.json"
)


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f, indent=4)


def load_events():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        return {}


def save_events(data):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def record_event(
    equipment_tag,
    event_type,
    message,
    severity="INFO",
    data=None
):
    """
    Record one chronological equipment event.
    """

    if not equipment_tag:
        return {
            "success": False,
            "message": "Equipment tag is required."
        }

    if not message:
        return {
            "success": False,
            "message": "Event message is required."
        }

    events = load_events()

    if equipment_tag not in events:
        events[equipment_tag] = []

    event = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "event_type": event_type,
        "severity": severity,
        "message": message,
        "data": data or {}
    }

    events[equipment_tag].append(event)

    save_events(events)

    return {
        "success": True,
        "event": event
    }


def get_events(equipment_tag):
    events = load_events()

    return events.get(
        equipment_tag,
        []
    )


def get_latest_event(equipment_tag):
    events = get_events(equipment_tag)

    if not events:
        return None

    return events[-1]


def get_event_count(equipment_tag):
    return len(
        get_events(equipment_tag)
    )


def get_recent_events(
    equipment_tag,
    limit=10
):
    events = get_events(equipment_tag)

    return events[-limit:]


def build_event_timeline(
    equipment_tag
):
    events = get_events(equipment_tag)

    return {
        "equipment": equipment_tag,
        "event_count": len(events),
        "events": events
    }
