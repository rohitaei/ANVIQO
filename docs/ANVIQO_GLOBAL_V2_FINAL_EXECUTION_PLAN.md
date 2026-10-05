# ANVIQO Global V2 — Final Execution Plan

## Wave 1 — Software foundation
Status: ENGINEERING CONTRACTS BUILT/TESTED
- tenant boundary
- safety boundary
- observation normalization
- edge registry
- evidence ledger
- realtime store
- replay
- event correlation
- evidence graph
- prediction validation
- causal boundary
- integration gateway
- time-series contract
- secure edge buffer
- edge ingestion bridge
- audit contract
- universal capability contracts
- final release gate
- PoV gate/checklist

## Wave 2 — First real plant
External implementation:
1. install approved read-only edge gateway;
2. connect approved S7/OPC UA/MQTT/Modbus source;
3. map tags and units;
4. verify clock/quality/sequence;
5. enable store-and-forward;
6. validate telemetry continuity;
7. validate alarms/events;
8. run ANVI evidence tests;
9. validate prediction/anomaly metrics;
10. validate maintenance recommendations;
11. collect operator/customer acceptance.

## Wave 3 — Production platform
External infrastructure:
- durable TSDB/event streaming;
- production evidence graph;
- IAM/SSO/MFA/RBAC;
- SIEM/security operations;
- HA/DR/backup;
- observability;
- API gateway/versioning;
- enterprise adapters;
- mobile production client;
- performance/load certification.

## Wave 4 — Global repeatability
- second plant using configuration/data only;
- measure onboarding effort;
- verify tenant isolation;
- verify identical intelligence behavior;
- benchmark outcomes;
- package deployment and support.

## Wave 5 — Commercial scale
- reference PoV;
- standard implementation package;
- pricing and SLA;
- enterprise sales/security package;
- partner/integrator model;
- multi-plant expansion.

## Hard rule
No plant-specific code fork. No PLC/SCADA write. No fake live data. No production deployment without external certification and explicit approval.
