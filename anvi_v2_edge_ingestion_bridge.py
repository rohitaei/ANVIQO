"""ANVIQO V2 edge-to-observation ingestion bridge.

This is a deterministic contract/simulation bridge. It does not implement or
claim live industrial protocol drivers. It converts an approved edge envelope
into the common observation contract and appends numeric telemetry to the V2
time-series contract. There is deliberately no control/write operation.
"""
from __future__ import annotations

from datetime import timezone

from anvi_global_v2_contracts import SUPPORTED_PROTOCOLS, normalize_observation, assert_tenant, safety_contract
from anvi_v2_secure_edge_runtime import EdgeEnvelope, SecureEdgeBuffer
from anvi_v2_timeseries_contract import TimeSeriesPoint, TimeSeriesStore

class EdgeIngestionBridge:
    def __init__(self, edge_buffer=None, time_series=None):
        self.edge_buffer = edge_buffer or SecureEdgeBuffer()
        self.time_series = time_series or TimeSeriesStore()

    def ingest(
        self,
        envelope: EdgeEnvelope,
        organization_id: str,
        plant_id: str,
        tag: str,
        value: float,
        quality: str = "GOOD",
        engineering_unit: str | None = None,
        source: str = "V2_EDGE",
    ) -> bool:
        envelope.validate()
        assert_tenant(envelope.organization_id, envelope.plant_id, organization_id, plant_id)
        protocol = envelope.protocol.upper()
        if protocol not in SUPPORTED_PROTOCOLS:
            raise ValueError("UNSUPPORTED_EDGE_PROTOCOL")
        if not self.edge_buffer.receive(envelope, organization_id, plant_id):
            return False

        normalized = normalize_observation(
            organization_id=organization_id,
            plant_id=plant_id,
            tag=tag,
            timestamp=envelope.observed_at.astimezone(timezone.utc).isoformat(),
            value=value,
            quality=quality,
            unit=engineering_unit or "",
            source_protocol=protocol,
            source_address=str(envelope.payload.get("source_address", "")),
            sequence=envelope.sequence,
        )
        if not normalized["valid"]:
            raise ValueError("INVALID_NORMALIZED_OBSERVATION")
        point = TimeSeriesPoint(
            organization_id=organization_id,
            plant_id=plant_id,
            tag=tag,
            timestamp=envelope.observed_at,
            value=value,
            engineering_unit=engineering_unit,
            quality=quality,
            source=source,
            sequence=envelope.sequence,
        )
        return self.time_series.append(point, organization_id, plant_id)

    def safety(self) -> dict:
        return {
            **safety_contract(),
            **self.edge_buffer.control_surface(),
            "control_path": "NONE",
        }
