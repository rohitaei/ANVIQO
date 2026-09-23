# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 20 VERIFIED

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

## Alpha 20 production boundary

Alpha 20 connects the real application Predictive Intelligence boundary to the canonical tenant-safe V3 package flow.

v3/production_boundary.py:
- requires explicit plant_id and organization_id
- loads only the requested active plant and its normalized onboarding knowledge
- rejects missing tenant scope
- rejects a plant belonging to another organization
- does not read legacy/global predictive stores
- delegates prediction execution to run_predictive_flow_from_package(...)

failure_prediction_api.py now uses this production boundary instead of directly invoking the legacy/global build_failure_prediction(...) path.

The API requires authenticated read access and explicit tenant context. Missing tenant context returns TENANT_CONTEXT_REQUIRED; there is no global fallback. Query/message, tag, observations, outcome, and optional evidence-window inputs are passed through the canonical flow.

The response preserves the canonical predictive result and execution provenance together with the read-only/human-decision safety boundary.

## Alpha 19 predictive execution provenance contract

Alpha 19 adds a deterministic provenance record to the canonical predictive flow.

The contract captures:
- exact plant and tag scope
- evidence quality and observation/window summary
- context assembly status
- predictor invocation status/reason
- explicit outcome-verification status
- immutable safety flags

The audit object is a contract builder only. It does not persist records, calculate predictions, interpret predictor output, infer outcomes, or perform control actions. Persistence remains the caller's responsibility.

## Universal and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Cross-plant prediction outcome: REJECTED
- Legacy/global predictor: BLOCKED on V3 path
- Legacy/global history: BLOCKED
- Legacy/global memory: BLOCKED
- Insufficient/partial evidence: predictor NOT INVOKED
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Alpha 10 dedicated V3 regression: **PASSED**.
Alpha 11 dedicated V3 regression: **PASSED** (run #88).
Alpha 12 dedicated V3 regression: **PASSED** (run #100).
Alpha 13 dedicated V3 regression: **PASSED** (run #114, 52 tests).
Alpha 14 dedicated V3 regression: **PASSED** (run #124, 52 tests).
Alpha 15 dedicated V3 regression: **PASSED** (run #134).
Alpha 16 dedicated V3 regression: **PASSED** (run #140, 55 tests).
Alpha 17 dedicated V3 regression: **PASSED** (run #150, 56 tests).
Alpha 18 dedicated V3 regression: **PASSED** (run #178, 60 tests).
Alpha 19 dedicated V3 regression: **PASSED** (run #188).
Alpha 20 dedicated V3 regression: **PASSED** (run #206, 64 passed).

Additional checks on Alpha 20 head:
- ANVIQO V2 Regression: **PASSED**
- Failure Prediction Dashboard workflow: **PASSED**

The branch remains separate and PR #40 remains draft/unmerged.

## Next safe milestone

Before adding another predictive feature, inspect the user-facing Predictive Intelligence API contract and add a focused production-boundary regression covering:
1. authenticated tenant context reaching the V3 flow
2. missing tenant context blocked without fallback
3. cross-organization plant access blocked
4. canonical evidence/window/prediction/provenance fields preserved at the API boundary
5. read-only/human-decision safety preserved

No new prediction, trend, RUL, diagnosis, threshold, or control engine may be introduced.

**CHANGE DATA, NOT CODE.**
