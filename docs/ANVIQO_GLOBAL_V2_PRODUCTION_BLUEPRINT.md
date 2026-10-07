# ANVIQO Global V2 — Production Blueprint

## Objective
A single universal ANVIQO product deployable across industrial plants without plant-specific reasoning forks.

## Production topology
Plant OT (PLC/DCS/SCADA) → read-only Edge Gateway → outbound TLS → ingestion/API → durable time-series + event stream → evidence graph → intelligence engines → ANVI/web/mobile → human decision.

## Global product planes
1. Identity & tenancy
2. OT/edge connectivity
3. Real-time telemetry
4. Evidence and provenance
5. Event correlation
6. Prediction/anomaly validation
7. Diagnosis/causal reasoning
8. Maintenance/spares
9. Command Centre
10. Conversational ANVI
11. Enterprise integrations
12. Governance/security/audit
13. Mobile/API experience
14. Resilience/observability

## Universal connector boundary
S7, OPC UA, MQTT/Sparkplug, Modbus TCP, file/API, CMMS/EAM/SAP and identity providers are adapter boundaries. A connector must normalize into the common evidence contract and remain read-only for OT.

## Global deployment requirements
- UTC time and synchronized clocks.
- Tenant and plant isolation at every query/write boundary.
- Durable storage and backup/recovery.
- HA and tested restore procedures.
- Metrics, logs, traces and alerting.
- IAM/RBAC with MFA/SSO where required.
- Encryption in transit and at rest.
- Secret management and rotation.
- Network segmentation and outbound-only OT transport.
- Versioned APIs and connector registry.
- Audit trail for user/system decisions.
- Load, resilience and security testing.
- Customer-specific regulatory/security review before production.

## Safety
read_only=True
plc_write=False
scada_control=False
automatic_authorization=False
automatic_execution=False
human_decision_required=True

## Promotion rule
No production promotion from this branch is implied by this document. Live OT connectivity, enterprise infrastructure and customer certification require external evidence and explicit approval.
