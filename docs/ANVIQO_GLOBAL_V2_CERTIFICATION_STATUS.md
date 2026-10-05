# ANVIQO Global V2 — Certification Status

## Purpose
This document prevents a contract from being mistaken for a production integration.

## Implemented and repository-tested contracts
- Universal tenant/safety contract
- Normalized industrial observation contract
- Read-only connector registry boundary for S7, OPC UA, MQTT, Sparkplug and Modbus TCP
- Evidence provenance ledger contract
- Append-only real-time telemetry/event store contract
- Time-series contract with UTC validation, quality and bounded queries
- Secure edge buffer with tenant isolation, deduplication and store-and-forward semantics
- Edge → normalized observation → time-series ingestion bridge
- Replay and event-correlation bridges
- Evidence graph temporal-association boundary
- Prediction/anomaly validation primitives
- Causal reasoning boundary that never upgrades temporal evidence to causation
- Integration gateway with OT write path blocked
- Audit/observability append-only contract
- Universal V2 capability/safety contracts

## Adapter / certification boundaries
These are designed interfaces, not claims of live connectivity or certification:
- Live Siemens S7 driver and plant gateway deployment
- Live OPC UA/MQTT/Sparkplug/Modbus drivers
- Durable production time-series database
- Production event streaming infrastructure
- Production evidence graph database
- Enterprise IAM/SSO/MFA
- SIEM/central audit infrastructure
- HA/DR/load certification
- CMMS/EAM/SAP production integrations
- Production Android client
- Production digital-twin, optimization and enterprise outcome-learning services

## Safety gate
`read_only=True`
`plc_write=False`
`scada_control=False`
`automatic_authorization=False`
`automatic_execution=False`
`human_decision_required=True`

No V2 component in this branch provides an automatic PLC/SCADA control path.

## Test rule
Repository tests are the evidence for contract correctness. A production capability is not certified until its external adapter, operational behavior, security controls and plant PoV are also tested and accepted.

## Deployment rule
This V2 branch is intentionally separate from frozen production. Do not deploy it to the production Render service until the user explicitly authorizes the V2 release gate.
