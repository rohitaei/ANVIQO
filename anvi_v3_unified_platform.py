"""ANVIQO V2→V3 unified industrial-intelligence facade.

This is the single universal orchestration layer for the V2→V3 capability set.
It composes normalized telemetry, alarms/events, What Changed, evidence graph,
anomaly/prediction validation, instrument/equipment/maintenance/shift and
energy/production/quality views. It is tenant-scoped and read-only toward OT.

IMPORTANT:
- This module does not open a PLC/SCADA write path.
- In-memory storage is a reference/demo backend, not a production TSDB.
- Production adapters must implement the same contracts and pass external PoV.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Iterable
import hashlib
import threading

from anvi_v2_realtime_store import TelemetryPoint, StreamEvent
from anvi_v2_evidence_graph import build_evidence_graph
from anvi_v2_prediction_validation import drift_signal
from anvi_v2_global_capability_contracts import TenantRef

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}

SEVERITY_ORDER = {"CRITICAL": 3, "WARNING": 2, "INFO": 1, "HEALTHY": 0}
QUALITY_BAD = {"BAD", "UNCERTAIN"}


@dataclass(frozen=True)
class PlatformEvent:
    organization_id: str
    plant_id: str
    event_type: str
    tag: str
    timestamp: datetime
    message: str
    severity: str = "INFO"
    source: str = "ANVIQO_V3"
    equipment: str = ""

    def stream(self) -> StreamEvent:
        return StreamEvent(
            self.organization_id, self.plant_id, self.event_type,
            self.timestamp, self.message, self.tag, self.equipment,
            self.severity, self.source
        ).normalized()


class UnifiedIndustrialPlatform:
    """Universal, deterministic V2→V3 intelligence reference implementation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._points: dict[str, TelemetryPoint] = {}
        self._events: dict[str, StreamEvent] = {}
        self._baselines: dict[tuple[str, str, str], float] = {}

    @staticmethod
    def _scope(org: str, plant: str) -> tuple[str, str]:
        if not org or not plant:
            raise ValueError("organization_id and plant_id are required")
        return str(org), str(plant)

    def set_baseline(self, org: str, plant: str, tag: str, value: float) -> None:
        org, plant = self._scope(org, plant)
        self._baselines[(org, plant, tag)] = float(value)

    def ingest(self, point: TelemetryPoint, *, selected_org: str, selected_plant: str) -> dict[str, Any]:
        """Accept normalized edge telemetry only when it matches the selected tenant."""
        self._scope(selected_org, selected_plant)
        if point.organization_id != selected_org or point.plant_id != selected_plant:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        if point.quality.upper() not in {"GOOD", "BAD", "UNCERTAIN"}:
            raise ValueError("INVALID_QUALITY")
        point_id = point.observation_id
        with self._lock:
            created = point_id not in self._points
            self._points.setdefault(point_id, point)
        return {
            "accepted": True,
            "deduplicated": not created,
            "observation_id": point_id,
            "safety": dict(SAFETY),
        }

    def add_event(self, event: PlatformEvent, *, selected_org: str, selected_plant: str) -> dict[str, Any]:
        if event.organization_id != selected_org or event.plant_id != selected_plant:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        normalized = event.stream()
        with self._lock:
            created = normalized.event_id not in self._events
            self._events.setdefault(normalized.event_id, normalized)
        return {"accepted": True, "deduplicated": not created, "event_id": normalized.event_id, "safety": dict(SAFETY)}

    def _points_for(self, org: str, plant: str, tag: str | None = None) -> list[TelemetryPoint]:
        org, plant = self._scope(org, plant)
        with self._lock:
            rows = [
                p for p in self._points.values()
                if p.organization_id == org and p.plant_id == plant
                and (tag is None or p.tag == tag)
            ]
        return sorted(rows, key=lambda p: p.timestamp)

    def _events_for(self, org: str, plant: str) -> list[StreamEvent]:
        org, plant = self._scope(org, plant)
        with self._lock:
            rows = [e for e in self._events.values()
                    if e.organization_id == org and e.plant_id == plant]
        return sorted(rows, key=lambda e: e.timestamp)

    def alarms(self, org: str, plant: str) -> dict[str, Any]:
        events = [e for e in self._events_for(org, plant) if e.event_type == "ALARM"]
        events.sort(key=lambda e: (-SEVERITY_ORDER.get(e.severity, 0), -e.timestamp.timestamp()))
        return {
            "status": "OK",
            "active_alarm_count": len(events),
            "critical_count": sum(e.severity == "CRITICAL" for e in events),
            "warning_count": sum(e.severity == "WARNING" for e in events),
            "alarms": [asdict(e) | {"timestamp": e.timestamp.isoformat()} for e in events[:100]],
            "recurrence_claim": False,
            "source": "V2_V3_EVENT_STREAM",
            "safety": dict(SAFETY),
        }

    def instrument(self, org: str, plant: str, tag: str) -> dict[str, Any]:
        rows = self._points_for(org, plant, tag)
        if not rows:
            return {"status": "NO DATA", "tag": tag, "evidence_status": "NO_EVIDENCE", "safety": dict(SAFETY)}
        values = [float(p.value) for p in rows if isinstance(p.value, (int, float))]
        baseline = self._baselines.get((org, plant, tag))
        flatline = len(values) >= 3 and len(set(values[-3:])) == 1
        bad_quality = sum(p.quality.upper() in QUALITY_BAD for p in rows)
        current = values[-1] if values else None
        return {
            "status": "OK",
            "tag": tag,
            "current_value": current,
            "engineering_unit": rows[-1].engineering_unit,
            "quality": rows[-1].quality,
            "last_timestamp": rows[-1].timestamp.isoformat(),
            "sample_count": len(rows),
            "health_flags": {
                "bad_or_uncertain_quality": bad_quality > 0,
                "flatline": flatline,
                "baseline_deviation": bool(baseline is not None and current is not None and drift_signal(current, baseline)),
            },
            "baseline": baseline,
            "evidence_status": "EVIDENCE_AVAILABLE",
            "safety": dict(SAFETY),
        }

    def equipment(self, org: str, plant: str, tag: str) -> dict[str, Any]:
        inst = self.instrument(org, plant, tag)
        events = [e for e in self._events_for(org, plant) if e.tag == tag or e.equipment == tag]
        if inst.get("status") == "NO DATA" and not events:
            return {"status": "NO DATA", "equipment": tag, "evidence_status": "NO_EVIDENCE", "safety": dict(SAFETY)}
        critical = sum(e.severity == "CRITICAL" for e in events)
        warning = sum(e.severity == "WARNING" for e in events)
        risk_band = "CRITICAL" if critical else ("WARNING" if warning or inst.get("health_flags", {}).get("baseline_deviation") else "NORMAL")
        return {
            "status": "OK",
            "equipment": tag,
            "risk_band": risk_band,
            "event_count": len(events),
            "instrument": inst,
            "evidence_status": "EVIDENCE_AVAILABLE",
            "causation_claimed": False,
            "safety": dict(SAFETY),
        }

    def what_changed(self, org: str, plant: str, tag: str | None = None) -> dict[str, Any]:
        rows = self._points_for(org, plant, tag)
        changes = []
        grouped: dict[str, list[TelemetryPoint]] = {}
        for p in rows:
            grouped.setdefault(p.tag, []).append(p)
        for t, pts in grouped.items():
            if len(pts) < 2:
                continue
            before, after = pts[-2], pts[-1]
            if before.value != after.value:
                numeric_delta = None
                if isinstance(before.value, (int, float)) and isinstance(after.value, (int, float)):
                    numeric_delta = float(after.value) - float(before.value)
                changes.append({
                    "tag": t,
                    "before": before.value,
                    "after": after.value,
                    "delta": numeric_delta,
                    "timestamp": after.timestamp.isoformat(),
                    "quality": after.quality,
                    "source": after.source,
                })
        events = self._events_for(org, plant)
        return {
            "status": "OK",
            "changes": changes,
            "related_events": [asdict(e) | {"timestamp": e.timestamp.isoformat()} for e in events[-100:]],
            "causation_claimed": False,
            "evidence_status": "EVIDENCE_AVAILABLE" if changes or events else "NO_EVIDENCE",
            "safety": dict(SAFETY),
        }

    def shift(self, org: str, plant: str, hours: int = 8) -> dict[str, Any]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=max(1, min(hours, 24)))
        points = [p for p in self._points_for(org, plant) if start <= p.timestamp <= end]
        events = [e for e in self._events_for(org, plant) if start <= e.timestamp <= end]
        return {
            "status": "OK",
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "telemetry_points": len(points),
            "events": len(events),
            "alarms": sum(e.event_type == "ALARM" for e in events),
            "critical_alarms": sum(e.event_type == "ALARM" and e.severity == "CRITICAL" for e in events),
            "quality_bad_points": sum(p.quality.upper() in QUALITY_BAD for p in points),
            "watch_list": sorted({e.tag or e.equipment for e in events if e.severity in {"CRITICAL", "WARNING"} and (e.tag or e.equipment)})[:20],
            "evidence_status": "EVIDENCE_AVAILABLE" if points or events else "NO_EVIDENCE",
            "safety": dict(SAFETY),
        }

    def energy_production_quality(self, org: str, plant: str, tags: Iterable[str] = ()) -> dict[str, Any]:
        requested = list(tags)
        data = {}
        for tag in requested:
            rows = self._points_for(org, plant, tag)
            vals = [float(p.value) for p in rows if isinstance(p.value, (int, float))]
            data[tag] = {
                "samples": len(vals),
                "latest": vals[-1] if vals else None,
                "average": mean(vals) if vals else None,
                "evidence_status": "EVIDENCE_AVAILABLE" if vals else "NO_EVIDENCE",
            }
        return {
            "status": "OK",
            "metrics": data,
            "optimization_claimed": False,
            "evidence_status": "EVIDENCE_AVAILABLE" if any(v["samples"] for v in data.values()) else "NO_EVIDENCE",
            "safety": dict(SAFETY),
        }

    def evidence_graph(self, org: str, plant: str, tag: str | None = None) -> dict[str, Any]:
        tenant = TenantRef(org, plant)
        telemetry = self._points_for(org, plant, tag)
        events = self._events_for(org, plant)
        graph = build_evidence_graph(tenant, telemetry, events)
        return {
            "status": "OK",
            "tenant": {"organization_id": org, "plant_id": plant},
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "relations": ["temporally_associated"] if graph.edges else [],
            "causal_claimed": graph.causal_claimed,
            "evidence_ids": [n.node_id for n in graph.nodes],
            "safety": dict(SAFETY),
        }

    def maintenance(self, org: str, plant: str) -> dict[str, Any]:
        events = self._events_for(org, plant)
        candidates = {}
        for e in events:
            if e.severity not in {"CRITICAL", "WARNING"}:
                continue
            key = e.tag or e.equipment or "UNKNOWN"
            candidates[key] = candidates.get(key, 0) + 1
        items = [
            {
                "equipment": tag,
                "attention_events": count,
                "decision": "MAINTENANCE REVIEW REQUIRED",
                "automatic_execution": False,
                "evidence_status": "EVIDENCE_AVAILABLE",
            }
            for tag, count in sorted(candidates.items(), key=lambda x: -x[1])[:20]
        ]
        return {"status": "OK", "items": items, "human_approval_required": True, "safety": dict(SAFETY)}

    def platform_summary(self, org: str, plant: str) -> dict[str, Any]:
        points = self._points_for(org, plant)
        events = self._events_for(org, plant)
        alarms = [e for e in events if e.event_type == "ALARM"]
        critical = sum(e.severity == "CRITICAL" for e in alarms)
        warning = sum(e.severity == "WARNING" for e in alarms)
        return {
            "product": "ANVIQO",
            "version": "V2.0→V3.0 UNIFIED INTELLIGENCE",
            "scope": {"organization_id": org, "plant_id": plant},
            "domains": {
                "real_time_telemetry": True,
                "time_series_contract": True,
                "alarms_events": True,
                "what_changed": True,
                "instrument_health": True,
                "equipment_reliability": True,
                "maintenance_spares": True,
                "shift_intelligence": True,
                "energy_production_quality": True,
                "evidence_graph": True,
                "prediction_validation": True,
                "causal_reasoning_boundary": True,
                "enterprise_identity_boundary": True,
                "audit_boundary": True,
                "secure_edge_boundary": True,
                "digital_twin_boundary": True,
                "optimization_boundary": True,
                "mobile_api_boundary": True,
            },
            "telemetry_points": len(points),
            "events": len(events),
            "active_alarms": len(alarms),
            "critical_alarms": critical,
            "warning_alarms": warning,
            "production_status": "ENGINEERING_COMPLETE / EXTERNAL_CERTIFICATION_PENDING",
            "safety": dict(SAFETY),
        }


platform = UnifiedIndustrialPlatform()


def register(app) -> None:
    """Register the V2→V3 API facade on the existing Flask app."""
    from flask import jsonify, request, session

    def actor():
        return session.get("organization_id", ""), session.get("plant_id", "")

    def require_scope():
        org, plant = actor()
        if not org or not plant:
            return None, jsonify({
                "status": "TENANT_UNAVAILABLE",
                "message": "Select an authenticated plant context first.",
                "safety": dict(SAFETY),
            }), 409
        return (org, plant), None, None

    @app.get("/api/v3/platform")
    def v3_platform():
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.platform_summary(*scope))

    @app.post("/api/v3/edge/envelope")
    def v3_edge_envelope():
        scope, err, code = require_scope()
        if err: return err, code
        body = request.get_json(silent=True) or {}
        try:
            from anvi_v2_edge_ingestion_bridge import EdgeIngestionBridge
            from anvi_v2_secure_edge_runtime import EdgeEnvelope
            ts = datetime.fromisoformat(str(body["observed_at"]).replace("Z", "+00:00"))
            env = EdgeEnvelope(
                scope[0], scope[1], str(body["protocol"]).upper(),
                int(body["sequence"]), ts, dict(body.get("payload") or {})
            )
            bridge = EdgeIngestionBridge()
            accepted = bridge.ingest(
                env, scope[0], scope[1], str(body["tag"]), body["value"],
                str(body.get("quality", "GOOD")).upper(),
                body.get("engineering_unit"), str(body.get("source", "READ_ONLY_EDGE"))
            )
            if accepted:
                ts_point = TelemetryPoint(
                    scope[0], scope[1], str(body["tag"]), ts, body["value"],
                    str(body.get("engineering_unit", "")),
                    str(body.get("quality", "GOOD")).upper(),
                    str(body.get("source", "READ_ONLY_EDGE")), int(body["sequence"])
                )
                platform.ingest(ts_point, selected_org=scope[0], selected_plant=scope[1])
            return jsonify({
                "status": "ACCEPTED" if accepted else "DEDUPLICATED",
                "tenant": {"organization_id": scope[0], "plant_id": scope[1]},
                "observation_accepted": bool(accepted),
                "protocol": env.protocol,
                "control_path": "NONE",
                "safety": bridge.safety(),
            }), 200
        except PermissionError as exc:
            return jsonify({"status": "FORBIDDEN", "message": str(exc), "safety": dict(SAFETY)}), 403
        except Exception as exc:
            return jsonify({"status": "BAD_REQUEST", "message": str(exc), "safety": dict(SAFETY)}), 400

    @app.post("/api/v3/edge/observations")
    def v3_ingest():
        scope, err, code = require_scope()
        if err: return err, code
        body = request.get_json(silent=True) or {}
        try:
            ts = datetime.fromisoformat(str(body["timestamp"]).replace("Z", "+00:00"))
            point = TelemetryPoint(
                scope[0], scope[1], str(body["tag"]), ts, body["value"],
                str(body.get("engineering_unit", "")), str(body.get("quality", "GOOD")).upper(),
                str(body.get("source", "EDGE")), body.get("sequence"),
            )
            return jsonify(platform.ingest(point, selected_org=scope[0], selected_plant=scope[1]))
        except PermissionError as exc:
            return jsonify({"status": "FORBIDDEN", "message": str(exc), "safety": dict(SAFETY)}), 403
        except Exception as exc:
            return jsonify({"status": "BAD_REQUEST", "message": str(exc), "safety": dict(SAFETY)}), 400

    @app.get("/api/v3/alarms")
    def v3_alarms():
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.alarms(*scope))

    @app.get("/api/v3/instrument/<tag>")
    def v3_instrument(tag):
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.instrument(*scope, tag))

    @app.get("/api/v3/equipment/<tag>")
    def v3_equipment(tag):
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.equipment(*scope, tag))

    @app.get("/api/v3/what-changed")
    def v3_changed():
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.what_changed(*scope, request.args.get("tag")))

    @app.get("/api/v3/evidence-graph")
    def v3_graph():
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.evidence_graph(*scope, request.args.get("tag")))

    @app.get("/api/v3/maintenance")
    def v3_maintenance():
        scope, err, code = require_scope()
        if err: return err, code
        return jsonify(platform.maintenance(*scope))

    @app.get("/api/v3/shift")
    def v3_shift():
        scope, err, code = require_scope()
        if err: return err, code
        try: hours = int(request.args.get("hours", "8"))
        except ValueError: hours = 8
        return jsonify(platform.shift(*scope, hours))

    @app.get("/api/v3/energy-production-quality")
    def v3_epq():
        scope, err, code = require_scope()
        if err: return err, code
        tags = [x.strip() for x in request.args.get("tags", "").split(",") if x.strip()]
        return jsonify(platform.energy_production_quality(*scope, tags))

    @app.get("/api/v3/safety")
    def v3_safety():
        return jsonify({"status": "SAFE READ-ONLY MODE", "safety": dict(SAFETY)})

    print("ANVIQO V2→V3 unified intelligence facade registered", flush=True)
