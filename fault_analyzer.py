def analyze_control_valve(answers):
    text = " ".join(str(v).lower() for v in answers.values())

    findings = []
    next_test = "Check the positioner and I/P converter."

    if "15 ma" in text or "16 ma" in text or "17 ma" in text or "18 ma" in text:
        findings.append("The command signal appears to be present.")

    if "20%" in text or "10%" in text or "0%" in text:
        findings.append("Valve position may be significantly different from the command.")

    if "low air" in text or "low pressure" in text:
        findings.append("Low instrument-air pressure may be preventing valve movement.")
        next_test = "Verify instrument-air pressure at the positioner."

    if "alarm" in text or "fault" in text:
        findings.append("A positioner or control fault may be contributing.")

    if not findings:
        findings.append("Insufficient evidence for a reliable fault conclusion.")

    return {
        "likely_fault": "Possible positioner, I/P, air-supply or mechanical problem.",
        "findings": findings,
        "next_test": next_test,
        "confidence": "Preliminary"
    }


def analyze(topic, answers):
    topic = topic.lower()

    if "control valve" in topic:
        return analyze_control_valve(answers)

    return {
        "likely_fault": "Insufficient diagnostic data.",
        "findings": ["More equipment-specific information is required."],
        "next_test": "Collect additional measurements.",
        "confidence": "Low"
    }
