# ANVIQO V2 - Real-Time Industrial Intelligence

Status: V2 FOUNDATION STARTED - ALPHA 1

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
-> read-only gateway/adapters
-> V2 Real-Time Data Fabric
-> V5 Frozen Intelligence
-> prediction / investigation / recommendation
-> human decision
-> Plant Memory
-> ROI

## Alpha 1 delivered

1. Normalized IndustrialPoint contract.
2. Bounded plant-scoped, tag-scoped read-only stream buffer.
3. Data-path health reporting.
4. Adapter for the existing PCI demo stream.
5. Regression tests for isolation, bounded history and safety.

## Next V2 build order

1. Real-time source adapter interface: OPC UA / MQTT / historian / existing demo.
2. Data trust and freshness layer.
3. Live Plant Brain orchestration using existing V5 engines.
4. WATCH state and anomaly/discovery orchestration.
5. Knowledge Graph / Equipment DNA context.
6. What Changed and alarm intelligence on the live stream.
7. End-to-end PT-303/304 abnormal-pressure demo with evidence, verified history, recovery and human verification.

V2 does not introduce a second prediction, root-cause, health or reasoning engine.
