# ANVIQO V2 - Real-Time Industrial Intelligence

Status: V2 FOUNDATION STARTED - ALPHA 1.6

## Frozen boundary

V5 remains frozen and read-only.

- PLC write: FALSE
- SCADA control: FALSE
- Automatic authorization: FALSE
- Automatic execution: FALSE
- Human decision required: TRUE
- V5 reasoning is reused, not duplicated.

## Architecture

PLC / SCADA / Historian / Demo Stream
-> read-only source adapters
-> V2 Real-Time Data Fabric
-> V5 Frozen Intelligence
-> prediction / investigation / recommendation
-> human decision
-> Plant Memory
-> ROI

## Alpha 1.1 delivered

1. Normalized IndustrialPoint contract.
2. Bounded plant-scoped, tag-scoped read-only stream buffer.
3. Data-path health reporting.
4. Transport-neutral read-only source adapter interface.
5. Adapter for the existing PCI demo stream.
6. FabricSourceRunner for one-shot source -> fabric polling.
7. Universal data trust and freshness policy with explicit evidence status.\n8. Universal Live Plant Brain orchestration that passes evidence into an injected existing-V5 bridge.\n9. Regression tests for normalization, plant isolation, safety, trust/freshness and Plant Brain tenant scoping.

No OPC UA/MQTT/Historian client is activated in this step. They will implement the same interface later.

## Next V2 build order

1. Data trust and freshness layer.
2. Live Plant Brain orchestration using existing V5 engines.
3. WATCH state and anomaly/discovery orchestration.
4. Knowledge Graph / Equipment DNA context.
5. What Changed and alarm intelligence on the live stream.
6. End-to-end PT-303/304 abnormal-pressure demo with evidence, verified history, recovery and human verification.

V2 does not introduce a second prediction, root-cause, health or reasoning engine. The trust layer is evidence gating/metadata only; it is not a reasoning engine.


## Alpha 1.4 delivered — WATCH + discovery orchestration

V2 now provides a universal WATCH/discovery coordinator around the read-only data fabric.

- WatchOrchestrator evaluates evidence freshness/quality metadata and generic value changes between observations.
- States are INSUFFICIENT_EVIDENCE, WATCH, or OBSERVE.
- A WATCH candidate is a discovery prompt, not an anomaly, prediction, diagnosis, alarm, or failure verdict.
- Existing V5 intelligence can be invoked only through an injected bridge.
- Plant scope is preserved; no global fallback is used.
- No plant-specific tags, thresholds, process rules, or reasoning are added.
- PLC write, SCADA control, and automatic action remain disabled.

This step deliberately does not activate OPC UA/MQTT/Historian clients and does not create a second anomaly, prediction, root-cause, health, alarm, or reasoning engine.


## Alpha 1.5 delivered — Equipment DNA context

V2 now includes a universal, plant-scoped Equipment DNA context layer. It stores supplied equipment identity and supplied relationships without inventing topology or process semantics. Normalized IndustrialPoint metadata can be converted into equipment nodes. Context is exposed as evidence for existing V5 intelligence; V2 does not add prediction, diagnosis, health, alarm, or control logic.

Safety remains read-only: PLC write FALSE, SCADA control FALSE, automatic action FALSE, human decision required TRUE.


## Alpha 1.6 delivered — live event context bridge

V2 now joins generic WATCH candidates with tenant-scoped Equipment DNA context and preserves an injected result from the existing V5 What Changed/Event intelligence.

- WATCH candidates remain evidence/discovery signals, not new alarms or diagnoses.
- Equipment DNA lookup is always scoped to the supplied plant.
- Existing V5 What Changed/Event intelligence remains authoritative; V2 does not duplicate it.
- No plant-specific thresholds, tags, process rules, or reasoning were added.
- Safety remains read-only: PLC write FALSE, SCADA control FALSE, automatic action FALSE, human decision required TRUE.
