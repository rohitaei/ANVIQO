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
