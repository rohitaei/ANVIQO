import struct
import pytest

from anvi_edge_gateway import GatewayConfig, ReadOnlyGateway
from anvi_s7_readonly import S7Tag, SiemensS7ReadOnlyAdapter


class FakeClient:
    def __init__(self):
        self.calls = []
        self.connected = False

    def connect(self, ip, rack, slot):
        self.calls.append(("connect", ip, rack, slot))
        self.connected = True

    def disconnect(self):
        self.calls.append(("disconnect",))
        self.connected = False

    def db_read(self, db, start, size):
        self.calls.append(("db_read", db, start, size))
        return struct.pack(">f", 43.5)

    def read_area(self, area, db, start, size):
        self.calls.append(("read_area", area, db, start, size))
        return bytes([1, 0])


def gateway():
    return ReadOnlyGateway(GatewayConfig("P1", "GW1", source="SIEMENS_S7", protocol="SIEMENS_S7"))


def test_real_decode_and_scaling_without_network():
    fake = FakeClient()
    adapter = SiemensS7ReadOnlyAdapter(gateway(), "10.0.0.1", snap7_client=fake)
    adapter.connect()
    result = adapter.read_one(S7Tag("PT-303", "DB", 10, 0, data_type="REAL", scale=2))
    assert result["value"] == pytest.approx(87.0)
    assert ("db_read", 10, 0, 4) in fake.calls
    assert not any("write" in str(call).lower() for call in fake.calls)


def test_process_image_and_bool_are_read_only():
    fake = FakeClient()
    adapter = SiemensS7ReadOnlyAdapter(gateway(), "10.0.0.1", snap7_client=fake)
    adapter.connect()
    result = adapter.read_one(S7Tag("MOTOR_RUN", "M", 0, 20, bit_offset=0, data_type="BOOL"))
    assert result["value"] is True
    assert result["protocol"] == "SIEMENS_S7"
    assert not any("write" in str(call).lower() for call in fake.calls)


def test_validation_blocks_invalid_configuration():
    with pytest.raises(ValueError):
        SiemensS7ReadOnlyAdapter(gateway(), "", snap7_client=FakeClient())
    with pytest.raises(ValueError):
        SiemensS7ReadOnlyAdapter(gateway(), "10.0.0.1", snap7_client=FakeClient()).validate_tag(
            S7Tag("", "DB")
        )


def test_no_write_surface():
    assert not any("write" in name.lower() for name in dir(SiemensS7ReadOnlyAdapter))
