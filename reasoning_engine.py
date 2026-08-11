def generate_reasoning(health_result):
    parameters = health_result.get("parameters", [])

    valve = None
    valve_direction = None
    valve_percentage = 0

    temperature = None
    temperature_direction = None
    temperature_percentage = 0

    air = None
    air_direction = None
    air_percentage = 0

    motor_current = None
    motor_current_direction = None
    motor_current_percentage = 0

    vibration = None
    vibration_direction = None
    vibration_percentage = 0

    conclusions = []
    recommendations = []
    evidence = []

    # -----------------------------------------
    # READ PARAMETER CONDITIONS
    # -----------------------------------------

    for item in parameters:

        message = item.get("message", "").lower()
        status = item.get("status")
        direction = item.get("direction")
        percentage = item.get("percentage_change", 0)

        if "valve position" in message:
            valve = status
            valve_direction = direction
            valve_percentage = percentage

        elif "temperature" in message:
            temperature = status
            temperature_direction = direction
            temperature_percentage = percentage

        elif "air pressure" in message:
            air = status
            air_direction = direction
            air_percentage = percentage

        elif "motor current" in message:
            motor_current = status
            motor_current_direction = direction
            motor_current_percentage = percentage

        elif "vibration" in message:
            vibration = status
            vibration_direction = direction
            vibration_percentage = percentage

    # -----------------------------------------
    # DEFAULT VALUES
    # -----------------------------------------

    priority = "LOW"
    risk_score = 0
    confidence = 50

    assessment = "No significant combined abnormality detected."

    first_check = "Continue normal monitoring."

    # -----------------------------------------
    # STRONG VALVE + TEMPERATURE + AIR PATTERN
    # -----------------------------------------

    if (
        valve == "EARLY WARNING"
        and valve_direction == "INCREASING"
        and temperature_direction == "INCREASING"
        and air_direction == "DECREASING"
        and air in ("WATCH", "EARLY WARNING")
    ):

        priority = "HIGH"

        # Risk calculation
        risk_score = 70

        if abs(valve_percentage) >= 50:
            risk_score += 5

        if abs(temperature_percentage) >= 15:
            risk_score += 5

        if abs(air_percentage) >= 10:
            risk_score += 5

        risk_score = min(risk_score, 100)

        confidence = 80

        assessment = (
            "Valve Position is increasing significantly while "
            "Temperature is rising and Instrument Air Pressure is falling. "
            "The combined pattern may indicate developing control-valve, "
            "positioner or instrument-air deterioration."
        )

        first_check = (
            "Verify instrument-air pressure directly at the valve positioner."
        )

        evidence.extend([
            f"Valve Position changed {valve_percentage}%.",
            f"Temperature changed {temperature_percentage}%.",
            f"Instrument Air Pressure changed {air_percentage}%."
        ])

        recommendations.extend([
            "Verify instrument-air pressure at the positioner.",
            "Check air regulator, tubing and possible leaks.",
            "Compare valve command with actual position feedback.",
            "Inspect positioner and I/P converter diagnostics.",
            "Review the process temperature trend."
        ])

    # -----------------------------------------
    # VALVE + TEMPERATURE
    # -----------------------------------------

    elif (
        valve == "EARLY WARNING"
        and valve_direction == "INCREASING"
        and temperature_direction == "INCREASING"
    ):

        priority = "HIGH"
        risk_score = 65
        confidence = 75

        if abs(valve_percentage) >= 50:
            risk_score += 5

        risk_score = min(risk_score, 100)

        assessment = (
            "Valve Position is increasing significantly while "
            "Temperature is also rising. This may indicate a developing "
            "control-loop or process abnormality."
        )

        first_check = (
            "Compare the valve command signal with actual valve position."
        )

        evidence.extend([
            f"Valve Position changed {valve_percentage}%.",
            f"Temperature changed {temperature_percentage}%."
        ])

        recommendations.extend([
            "Check valve command versus actual position feedback.",
            "Check positioner and I/P converter.",
            "Review process temperature trend.",
            "Check whether the valve is approaching its operating limit."
        ])

    # -----------------------------------------
    # VALVE + AIR
    # -----------------------------------------

    elif (
        valve_direction == "INCREASING"
        and valve in ("WATCH", "EARLY WARNING")
        and air_direction == "DECREASING"
        and air in ("WATCH", "EARLY WARNING")
    ):

        priority = "HIGH"
        risk_score = 65
        confidence = 75

        if abs(air_percentage) >= 10:
            risk_score += 5

        risk_score = min(risk_score, 100)

        assessment = (
            "Valve Position is increasing while Instrument Air Pressure "
            "is decreasing. This may indicate developing instrument-air "
            "or valve-positioner deterioration."
        )

        first_check = (
            "Verify instrument-air pressure directly at the positioner."
        )

        evidence.extend([
            f"Valve Position changed {valve_percentage}%.",
            f"Instrument Air Pressure changed {air_percentage}%."
        ])

        recommendations.extend([
            "Check instrument-air pressure.",
            "Check regulator, tubing and possible leaks.",
            "Inspect positioner and I/P converter.",
            "Compare valve command with actual position feedback."
        ])

    # -----------------------------------------
    # MOTOR CURRENT + VIBRATION
    # -----------------------------------------

    elif (
        motor_current_direction == "INCREASING"
        and motor_current in ("WATCH", "EARLY WARNING")
        and vibration_direction == "INCREASING"
        and vibration in ("WATCH", "EARLY WARNING")
    ):

        priority = "HIGH"
        risk_score = 65
        confidence = 75

        if abs(motor_current_percentage) >= 15:
            risk_score += 5

        if abs(vibration_percentage) >= 15:
            risk_score += 5

        risk_score = min(risk_score, 100)

        assessment = (
            "Motor Current and Vibration are increasing together. "
            "This may indicate increasing mechanical load, alignment "
            "problems, bearing deterioration or another rotating-equipment issue."
        )

        first_check = (
            "Check motor load, current balance and mechanical condition."
        )

        evidence.extend([
            f"Motor Current changed {motor_current_percentage}%.",
            f"Vibration changed {vibration_percentage}%."
        ])

        recommendations.extend([
            "Check motor load and current balance.",
            "Check coupling and alignment.",
            "Inspect bearings and rotating equipment.",
            "Review vibration trend and alarm limits."
        ])

    # -----------------------------------------
    # GENERAL PRIORITY
    # -----------------------------------------

    else:

        early = sum(
            1
            for item in parameters
            if item.get("status") == "EARLY WARNING"
        )

        watch = sum(
            1
            for item in parameters
            if item.get("status") == "WATCH"
        )

        if early >= 2:
            priority = "HIGH"
            risk_score = min(60 + early * 5, 100)
            confidence = 65

            assessment = (
                f"{early} parameters show early-warning trends. "
                "The combined condition requires engineering review."
            )

            first_check = (
                "Review the highest-severity parameters and their related process conditions."
            )

        elif early == 1:
            priority = "MEDIUM"
            risk_score = 50
            confidence = 60

            assessment = (
                "One parameter shows an early-warning trend and "
                "should be investigated before the condition develops further."
            )

            first_check = (
                "Investigate the parameter showing the early-warning trend."
            )

        elif watch >= 2:
            priority = "MEDIUM"
            risk_score = 40
            confidence = 55

            assessment = (
                f"{watch} parameters are showing watch-level trends. "
                "Continue close monitoring and investigate developing changes."
            )

            first_check = (
                "Monitor the affected parameters and compare them with process conditions."
            )

        elif watch == 1:
            priority = "LOW"
            risk_score = 20
            confidence = 50

            assessment = (
                "One parameter is showing a watch-level trend."
            )

            first_check = (
                "Continue monitoring the parameter."
            )

    # -----------------------------------------
    # RISK LEVEL
    # -----------------------------------------

    if risk_score >= 80:
        risk_level = "HIGH"
    elif risk_score >= 60:
        risk_level = "MODERATE-HIGH"
    elif risk_score >= 40:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # -----------------------------------------
    # FINAL OUTPUT
    # -----------------------------------------

    return {
        "priority": priority,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "assessment": assessment,
        "first_check": first_check,
        "evidence": list(dict.fromkeys(evidence)),
        "conclusion": [assessment],
        "recommendations": list(dict.fromkeys(recommendations))
    }
