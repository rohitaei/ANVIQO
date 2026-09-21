# ANVIQO V2 - Real-Time Industrial Intelligence

Status: V2 FOUNDATION STARTED - ALPHA 1.1

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
7. Regression tests for normalization, plant isolation and safety.

No OPC UA/MQTT/Historian client is activated in this step. They will implement the same interface later.

## Next V2 build order

1. Data trust and freshness layer.
2. Live Plant Brain orchestration using existing V5 engines.
3. WATCH state and anomaly/discovery orchestration.
4. Knowledge Graph / Equipment DNA context.
5. What Changed and alarm intelligence on the live stream.
6. End-to-end PT-303/304 abnormal-pressure demo with evidence, verified history, recovery and human verification.

V2 does not introduce a second prediction, root-cause, health or reasoning engine.
