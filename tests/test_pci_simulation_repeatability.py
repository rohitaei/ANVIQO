import pci_live_simulator as simulator


def test_simulation_window_replays_identical_values_and_timestamp():
    record = {
        "tag": "PT-303",
        "description": "Mill outlet gas pressure",
        "area": "VRM/MILL",
        "io_type": "AI",
        "plc_address": "PIW 260",
    }
    window_a, timestamp_a = simulator.reset_simulation_window(123456)
    first = simulator.simulate_point(record)
    window_b, timestamp_b = simulator.reset_simulation_window(123456)
    second = simulator.simulate_point(record)
    assert window_a == window_b == 123456
    assert timestamp_a == timestamp_b
    assert first == second
    assert first["mode"] == "SIMULATION"
    assert first["source"] == "PCI DEMO STREAM"


def test_simulation_window_keeps_plc_and_scada_writes_blocked():
    simulator.reset_simulation_window(123457)
    point = simulator.simulate_point({"tag": "PT-304", "io_type": "AI"})
    assert point["mode"] == "SIMULATION"
    # Simulator points carry no write or actuation command fields.
    assert not any("write" in key.lower() or "command" in key.lower() for key in point)



def test_missing_approved_signal_configuration_is_unassessed_not_healthy():
    simulator.reset_simulation_window(123458)
    point = simulator.simulate_point({
        "tag": "PT-303", "io_type": "AI (4-20mA)",
    })
    assert point["state"] == "UNASSESSED"
    assert point["assessment_basis"] == "NO_APPROVED_SIGNAL_LIMITS_OR_STATE_SEMANTICS"
    assert point["changed"] is False
    assert point["event_active"] is False


def test_analog_state_uses_only_explicit_approved_limits():
    limits = {
        "approved": True,
        "low": 0, "high": 100,
        "critical_low": 5, "warning_low": 10,
        "warning_high": 90, "critical_high": 95,
    }
    assert simulator._state({"io_type": "AI", "approved_engineering_limits": limits}, 50) == "HEALTHY"
    assert simulator._state({"io_type": "AI", "approved_engineering_limits": limits}, 92) == "WARNING"
    assert simulator._state({"io_type": "AI", "approved_engineering_limits": limits}, 98) == "CRITICAL"
    assert simulator._state({"io_type": "AI", "approved_engineering_limits": {**limits, "approved": False}}, 50) == "UNASSESSED"


def test_digital_state_requires_approved_signal_semantics():
    assert simulator._state({"io_type": "DI"}, 1) == "UNASSESSED"
    semantics = {"approved": True, "normal_states": [1], "alarm_states": [0]}
    assert simulator._state({"io_type": "DI", "approved_signal_semantics": semantics}, 1) == "HEALTHY"
    assert simulator._state({"io_type": "DI", "approved_signal_semantics": semantics}, 0) == "WARNING"
