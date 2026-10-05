# ANVIQO Global V2 — Plant PoV Runbook

## Purpose
Move ANVIQO from the V2 engineering foundation to a controlled first-plant Proof of Value (PoV) without modifying frozen V1 production.

## Mandatory deployment path
Simulation → Evidence → Read-only Edge → Secure Outbound Transport → Real Plant PoV → Measured Outcomes → Second-Plant Repeatability → Production Certification.

## PoV boundary
- Read-only telemetry only.
- No PLC write.
- No SCADA control.
- No automatic authorization.
- No automatic execution.
- Human decision required.
- Selected plant is authoritative; no cross-plant fallback.
- Simulation must never be presented as live telemetry.

## First PoV scope
1. Plant identity and tenant isolation.
2. Read-only edge connectivity.
3. Time-series telemetry ingestion.
4. Alarm/state/event correlation.
5. What Changed with evidence.
6. ANVI evidence-backed conversational reasoning.
7. Instrument/PCI identity resolution.
8. Prediction/anomaly validation.
9. Maintenance/spares decision support.
10. Audit trail and operator review.

## Acceptance evidence
The PoV is successful only when evidence is captured for:
- telemetry continuity and timestamp quality;
- duplicate handling and reconnect behavior;
- tenant isolation;
- alarm/event correlation;
- traceable evidence for ANVI answers;
- prediction/anomaly validation metrics;
- maintenance recommendation verification;
- safety-boundary enforcement;
- audit completeness;
- measurable plant outcome agreed with the customer.

## External infrastructure still required
This repository contract does not claim that live Siemens S7, OPC UA, MQTT/Sparkplug, Modbus TCP, durable time-series databases, event streaming, IAM/SSO/MFA, SIEM, HA/DR, or enterprise integrations are connected. Those require plant/customer infrastructure and certification evidence.

## Release rule
V2 may be promoted toward production only after the external evidence gates pass and the user explicitly authorizes deployment. Frozen V1 production remains untouched.
