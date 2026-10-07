"""Tenant-safe V2 evidence graph bridge.

Builds a deterministic graph from normalized telemetry/events. Edges represent
temporal/identity association only; this module never claims physical causality.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from anvi_v2_global_capability_contracts import TenantRef, EvidenceNode, CausalEdge, assert_tenant
from anvi_v2_realtime_store import TelemetryPoint, StreamEvent


@dataclass(frozen=True)
class EvidenceGraph:
    tenant: TenantRef
    nodes: tuple[EvidenceNode, ...]
    edges: tuple[CausalEdge, ...]

    @property
    def causal_claimed(self) -> bool:
        return False


def build_evidence_graph(
    tenant: TenantRef,
    telemetry: Iterable[TelemetryPoint] = (),
    events: Iterable[StreamEvent] = (),
    window_seconds: int = 300,
) -> EvidenceGraph:
    if window_seconds < 0:
        raise ValueError("window_seconds must be non-negative")
    points = list(telemetry or ())
    stream_events = list(events or ())
    nodes: list[EvidenceNode] = []

    for point in points:
        if point.organization_id != tenant.organization_id or point.plant_id != tenant.plant_id:
            raise PermissionError("CROSS_TENANT_ACCESS_BLOCKED")
        nodes.append(EvidenceNode(
            tenant, point.observation_id, "TELEMETRY", point.tag,
            point.timestamp, point.source,
        ))

    for event in stream_events:
        normalized = event.normalized()
        assert_tenant(TenantRef(normalized.organization_id, normalized.plant_id), tenant)
        nodes.append(EvidenceNode(
            tenant, normalized.event_id, "EVENT",
            normalized.tag or normalized.event_type,
            normalized.timestamp, normalized.source,
        ))

    nodes.sort(key=lambda n: (n.observed_at, n.node_id))
    edges: list[CausalEdge] = []
    for left, right in zip(nodes, nodes[1:]):
        if right.observed_at - left.observed_at <= timedelta(seconds=window_seconds):
            if left.label == right.label or "TELEMETRY" != "EVENT":
                edges.append(CausalEdge(
                    tenant, left.node_id, right.node_id,
                    "temporally_associated", 1.0, (left.node_id, right.node_id),
                ))
    return EvidenceGraph(tenant, tuple(nodes), tuple(edges))
