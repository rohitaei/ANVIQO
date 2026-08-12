DIAGNOSTICS = {
    "control valve": {
        "questions": [
            "What is the valve command signal in mA or %?",
            "What is the actual valve position feedback?",
            "What is the instrument air pressure?",
            "Is the positioner showing any alarm or fault?",
            "What is the I/P converter output?"
        ],
        "logic": {
            "command_low": "Check the PLC/DCS output, interlocks, permissives and control logic.",
            "air_low": "Check instrument-air supply, regulator, tubing and leaks.",
            "feedback_wrong": "Check valve position feedback, positioner calibration and mechanical linkage.",
            "positioner_fault": "Inspect the positioner configuration, diagnostics and wiring.",
            "ip_fault": "Check the I/P converter input, output and air supply."
        }
    },

    "4-20 ma": {
        "questions": [
            "What loop current are you measuring?",
            "What is the transmitter power supply voltage?",
            "Is the PLC/DCS analog input receiving the same current?",
            "Is the transmitter configured for the correct range?"
        ]
    },

    "rtd": {
        "questions": [
            "What temperature is the transmitter indicating?",
            "What resistance are you measuring at the RTD?",
            "Is it a 2-wire, 3-wire or 4-wire RTD?",
            "What RTD type is configured?"
        ]
    },

    "thermocouple": {
        "questions": [
            "What thermocouple type is installed?",
            "What temperature is being indicated?",
            "Is the polarity correct?",
            "Is the extension/compensating cable correct?"
        ]
    }
}


def start_diagnosis(topic):
    topic = topic.lower()

    for key in DIAGNOSTICS:
        if key in topic:
            data = DIAGNOSTICS[key]

            return {
                "topic": key,
                "question": data["questions"][0],
                "remaining_questions": data["questions"][1:],
                "logic": data.get("logic", {})
            }

    return None
