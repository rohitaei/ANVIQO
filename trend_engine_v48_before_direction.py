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

    if percentage >= 20:
        status = "EARLY WARNING"
        message = f"{name} is increasing significantly."
    elif percentage >= 10:
        status = "WATCH"
        message = f"{name} shows an increasing trend."
    else:
        status = "NORMAL"
        message = f"{name} does not show a significant increase."

    return {
        "status": status,
        "first": first,
        "last": last,
        "change": round(change, 2),
        "percentage_change": round(percentage, 2),
        "message": message
    }
