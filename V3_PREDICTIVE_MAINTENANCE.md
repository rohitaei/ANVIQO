# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 28 VERIFIED

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED
4. **Universal Predictive Evidence Quality & Window Contract** — VERIFIED
5. **Tenant-safe Predictive History Provider Bridge** — VERIFIED
6. **Canonical Tenant-safe Predictor Invocation Path** — VERIFIED
7. **Tenant-safe Maintenance Memory Bridge** — VERIFIED
8. **Canonical Tenant-safe Predictive Context** — VERIFIED
9. **Canonical Tenant-safe Prediction Result Contract** — VERIFIED
10. **Canonical Predictive Flow Boundary** — VERIFIED
11. **Predictive Outcome Verification Integration** — VERIFIED
12. **Tenant-safe Integration of Existing Predictor Sources** — VERIFIED
13. **Real Tenant-Scoped Predictive Evidence Providers** — VERIFIED
14. **Canonical Predictive Flow from Universal Plant Package** — VERIFIED
15. **Complete Real Evidence Context Composition** — VERIFIED
16. **Predictive Evidence Window & Trust Integration** — VERIFIED
17. **Predictive Trust/Freshness Decision Boundary** — VERIFIED
18. **Predictive Evidence Freshness Window Contract** — VERIFIED
19. **Predictive Execution Provenance Contract** — VERIFIED
20. **Predictive Flow Production Boundary Inspection** — VERIFIED
21. **Predictive Intelligence API Boundary** — VERIFIED
22. **Cross-Organization Predictive API Boundary Regression** — VERIFIED
23. **Predictive API Provenance Contract Regression** — VERIFIED
24. **Predictive Production Tenant Integration Regression** — VERIFIED
25. **Predictive Production History Tenant Boundary** — VERIFIED
26. **Predictive Production Data → V3 History Integration** — VERIFIED
27. **Recorded Tenant History → Canonical Predictive Evidence** — VERIFIED
28. **Read-only IndustrialPoint → Tenant Predictive History Adapter Seam** — VERIFIED

## Alpha 28 — production observation source integration boundary

The production observation path now has a universal, read-only adapter seam from the existing V2 `IndustrialPoint` contract into the existing tenant-scoped predictive history store.

The path is:

`Read-only source adapter → IndustrialPoint → tenant-scoped observation history → existing V3 evidence gate → existing predictor`

The Alpha 28 bridge:
- requires explicit `plant_id` and `organization_id`
- requires the IndustrialPoint plant identity to match exactly
- preserves tag, timestamp, numeric value, source, unit, state, area and provenance
- rejects simulation/demo points from production predictive history
- reuses the existing `record_tenant_observation` storage contract
- adds no PLC/SCADA write path
- adds no polling implementation or invented telemetry
- adds no prediction, trend, RUL, diagnosis, threshold or control logic

### Important source finding

The repository does **not** currently contain a production component that automatically reads real PLC/SCADA/OPC telemetry and feeds the observation endpoint.

The existing V2 `ReadOnlySourceAdapter` is deliberately transport-neutral, and the current PCI adapter is explicitly a simulation/demo adapter. Therefore Alpha 28 verifies the **safe source boundary**, not live telemetry connectivity.

Actual live telemetry requires a real plant-specific transport configuration behind the universal adapter contract; ANVIQO intelligence remains unchanged.

## Universal and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Cross-plant prediction outcome: REJECTED
- Cross-organization plant access: REJECTED
- Legacy/global predictor: BLOCKED on V3 path
- Legacy/global history: BLOCKED
- Legacy/global memory: BLOCKED
- Simulation/demo observations: NOT ELIGIBLE for production history
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Alpha 20 dedicated V3 regression: **PASSED** (run #206, 64 passed).
Alpha 21 dedicated V3 regression: **PASSED** (run #225).
Alpha 22 dedicated V3 regression: **PASSED** (run #231).
Alpha 23 dedicated V3 regression: **PASSED** (run #238, 70 passed).
Alpha 24 dedicated V3 regression: **PASSED** (run #243).
Alpha 25 dedicated V3 regression: **PASSED** (run #258, production history boundary tests included).
Alpha 26 dedicated V3 regression: **PASSED** (run #268, production history injection regression included).
Alpha 27 dedicated V3 regression: **PASSED** (run #275, production-history-to-evidence regression included).
Alpha 28 dedicated V3 regression: **PASSED** (run #279, read-only IndustrialPoint adapter regressions included).

PR #40 remains draft/unmerged.

## Important live-status distinction

Alpha 28 verifies the source boundary and regression contract in CI. It does **not** prove that a live Render plant is currently receiving real PLC/SCADA/OPC telemetry. No such claim is being made.

## Next safe milestone

**Alpha 29 — Real read-only source adapter integration contract.**

Focus:
1. define the transport-neutral handoff from an actual read-only source into `IndustrialPoint`
2. require explicit plant identity and source provenance at ingestion
3. reject simulation/demo sources at the production boundary
4. preserve timestamp/value/quality/unit/state evidence
5. keep the existing V3 predictor and evidence gate unchanged
6. do not invent protocol credentials, PLC polling, or plant-specific reasoning

The actual protocol (OPC UA, MQTT, historian/API, etc.) must be supplied/configured as a source adapter; the intelligence layer must remain universal.

**CHANGE DATA, NOT CODE.**
