"""
ANVIQO COMMAND INTENT LAYER
============================

Converts natural-language ANVI requests into structured intent.

IMPORTANT:
- Does NOT execute PLC/SCADA commands.
- Does NOT bypass ANVI reasoning.
- Does NOT modify the V5 engine.
- Control requests are sent only to anvi_control_gateway.
- Current execution mode is SIMULATION.
- Human approval remains mandatory.
"""

import re

from anvi_control_gateway import (
    create_control_request,
    control_capabilities,
)


CONTROL_VERBS = (
    "start",
    "stop",
    "open",
    "close",
    "enable",
    "disable",
    "reset",
    "set",
    "write",
    "change",
    "turn on",
    "turn off",
    "increase",
    "decrease",
)


def _normalise(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _extract_tag(text):
    """
    Extract known industrial-style tags.

    Examples:
        PT_303
        PT303
        FV_101
        P_201
        LT-202
    """

    match = re.search(
        r"\b[A-Z]{1,8}[_-]?\d{1,6}\b",
        text.upper(),
    )

    return match.group(0) if match else None


def _extract_value(text):
    """
    Extract a requested numeric value.

    Examples:
        40%
        25
        75.5
    """

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*%?\b",
        text,
    )

    if not match:
        return None

    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _looks_like_control(text):
    lower = text.lower()

    return any(
        verb in lower
        for verb in CONTROL_VERBS
    )


def classify_command(question):
    """
    Classify a user request.

    Returns:
        INFORMATION
        CONTROL
        UNKNOWN
    """

    q = _normalise(question)

    if not q:
        return {
            "intent": "UNKNOWN",
            "question": q,
        }

    if _looks_like_control(q):
        return {
            "intent": "CONTROL",
            "question": q,
        }

    return {
        "intent": "INFORMATION",
        "question": q,
    }


def build_control_intent(question):
    """
    Build a safe structured control intent.
    """

    q = _normalise(question)
    lower = q.lower()

    tag = _extract_tag(q)
    value = _extract_value(q)

    command = None

    if "start" in lower:
        command = "START"

    elif "stop" in lower:
        command = "STOP"

    elif "open" in lower:
        command = "OPEN"

    elif "close" in lower:
        command = "CLOSE"

    elif "reset" in lower:
        command = "RESET"

    elif "enable" in lower:
        command = "ENABLE"

    elif "disable" in lower:
        command = "DISABLE"

    elif "turn on" in lower:
        command = "TURN_ON"

    elif "turn off" in lower:
        command = "TURN_OFF"

    elif "set" in lower or "write" in lower:
        command = "SET"

    elif "increase" in lower:
        command = "INCREASE"

    elif "decrease" in lower:
        command = "DECREASE"

    return {
        "intent": "CONTROL",
        "command": command or "UNSPECIFIED",
        "tag": tag,
        "value": value,
        "question": q,
        "mode": "SIMULATION",
        "requires_human_approval": True,
    }


def handle_command(
    question,
    requested_by="TECHNICIAN",
    source="TEXT",
):
    """
    Classify and, for control requests, create a pending
    simulation control request.

    This function NEVER executes a real control operation.
    """

    classification = classify_command(question)

    if classification["intent"] != "CONTROL":
        return {
            "success": True,
            "intent": classification["intent"],
            "question": classification["question"],
            "control_created": False,
            "message": (
                "Information request. "
                "Route this through the existing ANVI knowledge/V5 layer."
            ),
        }

    intent = build_control_intent(question)

    if intent["command"] == "UNSPECIFIED":
        return {
            "success": False,
            "intent": "CONTROL",
            "message": "Control request detected, but command could not be identified.",
            "mode": "SIMULATION",
        }

    request = create_control_request(
        command=intent["command"],
        tag=intent["tag"],
        parameter=None,
        value=intent["value"],
        requested_by=requested_by,
        source=source,
    )

    return {
        "success": request.get("success", False),
        "intent": intent,
        "control_created": True,
        "mode": "SIMULATION",
        "approval_required": True,
        "request": request.get("request"),
        "message": request.get("message"),
    }


if __name__ == "__main__":

    print("==============================================")
    print(" ANVIQO COMMAND INTENT LAYER TEST")
    print("==============================================")

    print("\nCAPABILITIES:")
    print(control_capabilities())

    tests = [
        "Tell me about PT_303",
        "Is PT_303 healthy?",
        "Set PT_303 to 40%",
        "Start the mill",
        "Stop the pump",
        "Open FV_101",
        "Close FV_101",
        "Reset P_201",
        "Write 50 to PT_303",
    ]

    for question in tests:

        print("\nTECHNICIAN:", question)

        try:
            result = handle_command(
                question,
                requested_by="SIMULATION_TECHNICIAN",
                source="TEST",
            )

            print("INTENT:", result.get("intent"))
            print("CONTROL CREATED:", result.get("control_created"))
            print("MODE:", result.get("mode"))

            if result.get("request"):
                print(
                    "REQUEST ID:",
                    result["request"].get("request_id"),
                )

                print(
                    "COMMAND:",
                    result["request"].get("command"),
                )

                print(
                    "TAG:",
                    result["request"].get("tag"),
                )

                print(
                    "VALUE:",
                    result["request"].get("value"),
                )

                print(
                    "APPROVAL:",
                    result["request"].get("approval_status"),
                )

                print(
                    "EXECUTION:",
                    result["request"].get("execution_status"),
                )

            print("MESSAGE:", result.get("message"))

        except Exception as e:
            print(
                "ERROR:",
                type(e).__name__,
                e,
            )

    print("\n==============================================")
    print("SIMULATION TEST COMPLETE")
    print("REAL PLC WRITE: DISABLED")
    print("REAL SCADA CONTROL: DISABLED")
    print("==============================================")
