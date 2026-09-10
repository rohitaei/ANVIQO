# ANVIQO Phase 5 — Live Evidence HOD View V1

The HOD/Management view is an integration layer over existing ANVIQO evidence. It reuses the unified plant evidence context and the frozen V5.7 Executive/HOD contract; it does not create a second reasoning engine.

Evidence flow:
Existing PCI LIVE / V5 area evidence → unified evidence context → V5.7 Executive/HOD contract → Phase 5 Management Brief → HOD Command Centre.

When the simulator is the source, the UI explicitly labels the view DEMO / SIMULATION EVIDENCE.

Governance:
- read_only: true
- plc_write: false
- scada_control: false
- automatic_authorization: false
- automatic_execution: false
- human_decision_required: true
- causation_claim: false

Equipment priority scores are not manufactured by this adapter; they appear only when supplied by an existing intelligence contract. Area health and simulator counters are displayed as evidence, not as real plant measurements.