def analyze_trend(values, name="Parameter"):
    if not values or len(values) < 2:
        return {
            "status": "INSUFFICIENT DATA",
            "message": "At least two readings are required."
        }

    try:
        numbers = [float(v) for v in values]
    except ValueError:
        return {
            "status": "INVALID DATA",
            "message": "Readings must be numeric."
        }

    first = numbers[0]
    last = numbers[-1]
    change = last - first

    if first != 0:
        percentage = (change / abs(first)) * 100
    else:
        percentage = 0

    # -----------------------------------------
    # V4.8 DIRECTION-AWARE TREND ANALYSIS
    # -----------------------------------------

    if percentage >= 20:
        status = "EARLY WARNING"
        direction = "INCREASING"
        message = f"{name} is increasing significantly."

    elif percentage >= 10:
        status = "WATCH"
        direction = "INCREASING"
        message = f"{name} shows an increasing trend."

    elif percentage <= -20:
        status = "EARLY WARNING"
        direction = "DECREASING"
        message = f"{name} is decreasing significantly."

    elif percentage <= -10:
        status = "WATCH"
        direction = "DECREASING"
        message = f"{name} shows a decreasing trend."

    else:
        status = "NORMAL"
        direction = "STABLE"
        message = f"{name} is relatively stable."

    return {
        "status": status,
        "first": first,
        "last": last,
        "change": round(change, 2),
        "percentage_change": round(percentage, 2),
        "direction": direction,
        "message": message
    }
