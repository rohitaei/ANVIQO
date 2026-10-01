"""ANVIQO Siemens S7 read-only adapter.

Optional plant-side dependency: python-snap7.
This module contains read operations only. It has no PLC write methods and
never exposes a write-capable client API to ANVIQO Cloud.

Configuration is data-driven so a new plant can add PLC/tag definitions
without changing ANVIQO intelligence code.
"""

from __future__ import annotations

import importlib
import math
import struct
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from anvi_edge_gateway import ReadOnlyGateway


@dataclass(frozen=True)
class S7Tag:
    tag: str
    area: str = "DB"
    db_number: int = 0
    byte_offset: int = 0
    bit_offset: Optional[int] = None
    data_type: str = "REAL"
    length: Optional[int] = None
    scale: float = 1.0
    offset: float = 0.0


class SiemensS7ReadOnlyAdapter:
    """Read PLC values and normalize them into ANVIQO evidence envelopes."""

    SUPPORTED_AREAS = {"DB", "M", "I", "Q", "PE", "PA"}
    SUPPORTED_TYPES = {
        "BOOL", "BYTE", "USINT", "SINT", "WORD", "UINT", "INT",
        "DWORD", "UDINT", "DINT", "REAL",
    }

    def __init__(
        self,
        gateway: ReadOnlyGateway,
        plc_ip: str,
        rack: int = 0,
        slot: int = 1,
        timeout_s: float = 5.0,
        snap7_client: Any = None,
    ):
        self.gateway = gateway
        self.plc_ip = str(plc_ip).strip()
        self.rack = int(rack)
        self.slot = int(slot)
        self.timeout_s = float(timeout_s)
        self._client = snap7_client
        self._connected = False

        if not self.plc_ip:
            raise ValueError("plc_ip is required")
        if self.rack < 0 or self.slot < 0:
            raise ValueError("rack and slot must be non-negative")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")

    @staticmethod
    def _snap7():
        try:
            return importlib.import_module("snap7")
        except ImportError as exc:
            raise RuntimeError(
                "python-snap7 is required on the plant-side edge host; "
                "install edge-requirements.txt"
            ) from exc

    def _client_or_create(self):
        if self._client is None:
            snap7 = self._snap7()
            self._client = snap7.client.Client()
        return self._client

    def connect(self) -> Dict[str, Any]:
        client = self._client_or_create()
        client.connect(self.plc_ip, self.rack, self.slot)
        self._connected = True
        return self.status()

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.disconnect()
        self._connected = False

    def status(self) -> Dict[str, Any]:
        return {
            "status": "CONNECTED" if self._connected else "DISCONNECTED",
            "protocol": "SIEMENS_S7",
            "plc_ip": self.plc_ip,
            "rack": self.rack,
            "slot": self.slot,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    @classmethod
    def validate_tag(cls, spec: S7Tag) -> None:
        if not spec.tag.strip():
            raise ValueError("tag is required")
        if spec.area.upper() not in cls.SUPPORTED_AREAS:
            raise ValueError(f"unsupported S7 area: {spec.area}")
        if spec.data_type.upper() not in cls.SUPPORTED_TYPES:
            raise ValueError(f"unsupported data type: {spec.data_type}")
        if spec.byte_offset < 0:
            raise ValueError("byte_offset must be non-negative")
        if spec.bit_offset is not None and not 0 <= spec.bit_offset <= 7:
            raise ValueError("bit_offset must be between 0 and 7")
        if spec.area.upper() == "DB" and spec.db_number < 0:
            raise ValueError("db_number must be non-negative")

    @classmethod
    def _size(cls, data_type: str, length: Optional[int]) -> int:
        t = data_type.upper()
        if t in {"BOOL", "BYTE", "USINT", "SINT"}:
            return 1
        if t in {"WORD", "UINT", "INT"}:
            return 2
        if t in {"DWORD", "UDINT", "DINT", "REAL"}:
            return 4
        if length is None or length < 1:
            raise ValueError("length is required for this data type")
        return int(length)

    @classmethod
    def decode(cls, data: bytes, spec: S7Tag) -> Any:
        t = spec.data_type.upper()
        if t == "BOOL":
            if spec.bit_offset is None:
                raise ValueError("BOOL requires bit_offset")
            value = bool(data[0] & (1 << spec.bit_offset))
        elif t in {"BYTE", "USINT"}:
            value = data[0]
        elif t == "SINT":
            value = struct.unpack(">b", data[:1])[0]
        elif t == "WORD":
            value = struct.unpack(">H", data[:2])[0]
        elif t == "UINT":
            value = struct.unpack(">H", data[:2])[0]
        elif t == "INT":
            value = struct.unpack(">h", data[:2])[0]
        elif t == "DWORD":
            value = struct.unpack(">I", data[:4])[0]
        elif t == "UDINT":
            value = struct.unpack(">I", data[:4])[0]
        elif t == "DINT":
            value = struct.unpack(">i", data[:4])[0]
        elif t == "REAL":
            value = struct.unpack(">f", data[:4])[0]
            if not math.isfinite(value):
                raise ValueError("non-finite REAL value")
        else:
            raise ValueError(f"unsupported data type: {spec.data_type}")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = value * spec.scale + spec.offset
        return value

    def _read_bytes(self, spec: S7Tag) -> bytes:
        self.validate_tag(spec)
        if not self._connected:
            raise RuntimeError("S7 adapter is not connected")

        client = self._client_or_create()
        size = self._size(spec.data_type, spec.length)
        area = spec.area.upper()

        if area == "DB":
            return bytes(client.db_read(spec.db_number, spec.byte_offset, size))

        # Test/injected clients do not need python-snap7 installed. The
        # production path still resolves the official snap7 area constants.
        try:
            snap7 = self._snap7()
            area_map = {
                "M": snap7.types.Areas.MK,
                "I": snap7.types.Areas.PE,
                "PE": snap7.types.Areas.PE,
                "Q": snap7.types.Areas.PA,
                "PA": snap7.types.Areas.PA,
            }
        except RuntimeError:
            if self._client is None:
                raise
            area_map = {
                "M": "M",
                "I": "I",
                "PE": "PE",
                "Q": "Q",
                "PA": "PA",
            }
        return bytes(client.read_area(area_map[area], 0, spec.byte_offset, size))

    def read_one(self, spec: S7Tag, quality: str = "GOOD") -> Dict[str, Any]:
        value = self.decode(self._read_bytes(spec), spec)
        return self.gateway.normalize(
            spec.tag,
            value,
            quality=quality,
            source="SIEMENS_S7",
            protocol="SIEMENS_S7",
        )

    def read_many(self, specs: Iterable[S7Tag]) -> Dict[str, Any]:
        observations: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        for spec in specs:
            try:
                observations.append(self.read_one(spec))
            except Exception as exc:
                rejected.append({"tag": spec.tag, "reason": str(exc)})
        return {
            "status": "OK" if not rejected else ("PARTIAL" if observations else "ERROR"),
            "observations": observations,
            "accepted": len(observations),
            "rejected": len(rejected),
            "rejected_records": rejected,
            "safety": {
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_decision_required": True,
                "automatic_authorization": False,
                "automatic_execution": False,
            },
        }
