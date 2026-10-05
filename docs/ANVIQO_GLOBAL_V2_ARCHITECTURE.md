# ANVIQO Global V2 — Industrial Intelligence Architecture

Status: DEVELOPMENT BASELINE
Parent: ANVIQO V1.0 frozen commit d01d6b90d67bf20e74f03d5764b27007bc7208d0
Production V1 is not modified by this branch.

## Objective
Evolve ANVIQO from a strong plant-intelligence PoV into a globally deployable industrial intelligence platform while preserving the frozen safety contract.

## Architecture
Plant OT -> Read-only Edge Gateway -> Secure Outbound Transport -> Ingestion/Time-Series -> Evidence Graph -> Intelligence Engines -> ANVI -> Human Decision.

## Core planes
1. Identity & tenancy: enterprise -> organization -> plant -> area -> unit -> equipment -> instrument/tag.
2. Evidence plane: documents, telemetry, events, alarms, maintenance, spares, reports and provenance.
3. Real-time plane: edge observations, buffering, timestamps, quality and sequence.
4. Intelligence plane: health, anomaly, prediction, diagnosis, correlation, causal reasoning, optimization and learning.
5. Experience plane: Command Centre, ANVI chat/voice, mobile and management views.
6. Governance plane: RBAC, audit, safety gates, cybersecurity, model governance and data lineage.

## Connectivity targets
OPC UA, Siemens S7, MQTT/Sparkplug, Modbus TCP and file/API ingestion. All plant-facing connectivity is read-only by default. PLC/SCADA write remains blocked.

## Global scale
No plant-specific reasoning forks. New plants are configured through data, hierarchy, mappings and approved connectors.

## Intelligence expansion
Existing V5 intelligence is reused. V2 adds missing infrastructure around it rather than replacing it.

## Future production requirements
High availability, durable time-series storage, event streaming, disaster recovery, observability, SSO/MFA, IEC 62443-aligned controls, enterprise APIs and load testing are required before global production certification.

## Non-negotiable safety
read_only=true
plc_write=false
scada_control=false
automatic_authorization=false
automatic_execution=false
human_decision_required=true
