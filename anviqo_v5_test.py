from equipment_database import get_equipment
from equipment_health import get_latest_health
from digital_equipment_twin import build_digital_twin
from area_health import build_area_health
from plant_health import build_plant_health


def check(name, condition):
    print(
        f"[{'PASS' if condition else 'FAIL'}] {name}"
    )
    return condition


print("\n========================================")
print(" ANVIQO V5 MASTER REGRESSION TEST")
print("========================================")

passed = 0
failed = 0

# 1. Equipment database
try:
    equipment_list = get_equipment()
    ok = check(
        "Equipment database",
        isinstance(equipment_list, list)
    )
except Exception as e:
    ok = check(
        "Equipment database",
        False
    )
    print("  ERROR:", e)

passed += ok
failed += not ok

# 2. CV-101
equipment = None

try:
    equipment = get_equipment("CV-101")
    ok = check(
        "CV-101 equipment identity",
        equipment is not None
    )
except Exception as e:
    ok = False
    check("CV-101 equipment identity", False)
    print("  ERROR:", e)

passed += ok
failed += not ok

if equipment:

    # 3. Equipment health
    try:
        health = get_latest_health("CV-101")
        ok = check(
            "CV-101 health data",
            health is not None
        )

        if health:
            print(
                f"  Risk: {health.get('risk_score')}"
            )
            print(
                f"  Status: {health.get('status')}"
            )

    except Exception as e:
        ok = False
        check("CV-101 health data", False)
        print("  ERROR:", e)

    passed += ok
    failed += not ok

    # 4. Digital twin
    try:
        twin = build_digital_twin("CV-101")

        ok = check(
            "Digital twin",
            twin is not None
        )

        if twin:
            print(
                "  Relationships:",
                twin.get("relationships", {})
                .get("relationship_count")
            )

    except Exception as e:
        ok = False
        check("Digital twin", False)
        print("  ERROR:", e)

    passed += ok
    failed += not ok

    # 5. Area health
    try:
        area = equipment.get("area")

        area_result = build_area_health(area)

        ok = check(
            "Automatic area health",
            area_result.get("health_score") is not None
        )

        if ok:
            print(
                f"  Area: {area_result.get('area')}"
            )
            print(
                f"  Health: {area_result.get('health_score')}"
            )
            print(
                f"  Status: {area_result.get('status')}"
            )
            print(
                f"  Equipment: "
                f"{area_result.get('equipment_count')}"
            )

    except Exception as e:
        ok = False
        check("Automatic area health", False)
        print("  ERROR:", e)

    passed += ok
    failed += not ok

    # 6. Plant health
    try:
        area_list = []

        areas = sorted({
            item.get("area")
            for item in equipment_list
            if item.get("area")
        })

        for area_name in areas:
            result = build_area_health(area_name)

            if result.get("health_score") is not None:
                area_list.append({
                    "area": area_name,
                    "health_score":
                        result["health_score"],
                    "status":
                        result["status"]
                })

        plant = build_plant_health(
            "Tata Steel Plant",
            area_list
        )

        ok = check(
            "Automatic plant health",
            plant.get("health", {})
            .get("health_score") is not None
        )

        if ok:
            ph = plant["health"]

            print(
                f"  Plant health: "
                f"{ph.get('health_score')}"
            )
            print(
                f"  Plant status: "
                f"{ph.get('status')}"
            )
            print(
                f"  Areas: "
                f"{ph.get('area_count')}"
            )

    except Exception as e:
        ok = False
        check("Automatic plant health", False)
        print("  ERROR:", e)

    passed += ok
    failed += not ok


print("\n========================================")
print(" TEST SUMMARY")
print("========================================")

print("PASSED:", passed)
print("FAILED:", failed)

if failed == 0:
    print("\nANVIQO V5 MASTER REGRESSION: PASS")
else:
    print("\nANVIQO V5 MASTER REGRESSION: ATTENTION REQUIRED")

print("========================================")
