# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 29 VERIFIED

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
29. **Universal Real Read-only IndustrialPoint Source Adapter Contract** — VERIFIED

## Alpha 29 — universal real read-only source adapter contract

Alpha 29 establishes the transport-neutral handoff for an actual read-only plant source.

The path is:

`Actual read-only source → IndustrialPointSourceAdapter → tenant validation → IndustrialPoint → existing data/predictive path`

The new adapter contract:
- requires an explicit `plant_id`
- requires every emitted object to be an `IndustrialPoint`
- requires exact plant identity matching
- requires tag, timestamp and source evidence
- rejects simulation/demo source or mode values
- preserves the original IndustrialPoint unchanged
- does not implement a protocol-specific transport
- does not add PLC/SCADA write capability
- does not add prediction, trend, RUL, diagnosis, threshold or control logic

Regression coverage includes:
- valid tenant-scoped live IndustrialPoint accepted
- cross-plant IndustrialPoint rejected
- simulation/demo IndustrialPoint rejected
- missing source evidence rejected
- existing PCI demo adapter remains explicitly simulation-only

### Important live-source finding

The repository still does **not** contain an actual OPC-UA, MQTT, Modbus, PLC, SCADA or historian transport implementation.

Therefore Alpha 29 verifies the **universal adapter contract**, not live plant telemetry connectivity.

The real transport must be supplied behind this contract. Once a permitted read-only source is available, its reader can emit `IndustrialPoint` records without changing the V3 predictor or ANVI intelligence layer.

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
Alpha 29 dedicated V3 regression: **PASSED** (run #287, live IndustrialPoint adapter contract regressions included).

PR #40 remains draft/unmerged.

## Important live-status distinction

Alpha 29 verifies the universal source adapter contract in CI. It does **not** prove that a live Render plant is currently receiving real PLC/SCADA/OPC telemetry. No such claim is being made.

## Next safe milestone

**Alpha 30 — Actual read-only plant source integration inspection.**

Focus:
1. identify what real read-only plant data source is actually available
2. inspect its connection/API/export contract before writing any transport code
3. map source fields into the existing `IndustrialPoint` contract
4. preserve plant and organization tenant identity
5. route the data into the existing V2/V3 evidence/history path
6. test with real source evidence without changing the predictor
7. keep PLC write, SCADA control and automatic action disabled

No protocol credentials or connection details will be invented. If no real source is available yet, Alpha 30 will stop at the integration contract rather than fabricate telemetry.

**CHANGE DATA, NOT CODE.**
