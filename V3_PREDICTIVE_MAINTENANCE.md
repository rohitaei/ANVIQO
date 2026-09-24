# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 23 VERIFIED

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

## Alpha 22 cross-organization boundary

Alpha 22 verifies that predictive requests cannot cross organization boundaries at the user-facing /api/ask predictive path.

The API path:
- requires authenticated read access
- requires explicit organization_id and plant_id
- passes both tenant identifiers into the production predictive boundary
- preserves the existing organization+plant authorization contract
- converts a production-boundary PermissionError into an explicit FORBIDDEN response
- never falls back to a global plant
- never invokes the legacy/global predictor when authorization fails

The regression test uses an organization/plant mismatch and proves the predictive flow is rejected while the legacy predictor remains uncalled.

No prediction algorithm, trend engine, RUL engine, diagnosis engine, threshold logic, or control capability was added.

## Alpha 21 API boundary

Alpha 21 connected the user-facing /api/ask predictive request path to the canonical V3 tenant-safe production flow.

The API preserves:
- tenant identity
- canonical predictive result
- execution provenance
- read-only/human-decision safety flags

Missing tenant context returns TENANT_CONTEXT_REQUIRED; no global fallback is permitted.

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

## Universal and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Cross-plant prediction outcome: REJECTED
- Cross-organization plant access: REJECTED
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

Alpha 20 dedicated V3 regression: **PASSED** (run #206, 64 passed).
Alpha 21 dedicated V3 regression: **PASSED** (run #225).
Alpha 22 dedicated V3 regression: **PASSED** (run #231).
Alpha 23 dedicated V3 regression: **PASSED** (run #238, 70 passed).

PR #40 remains draft/unmerged.

## Next safe milestone

**Alpha 24 — Predictive production integration regression.**

Focus:
1. inspect the real production predictive path end-to-end after the API provenance boundary
2. verify tenant-scoped normalized onboarding data reaches the canonical flow without global fallback
3. verify cross-organization rejection and provenance remain intact at the production boundary
4. preserve read-only/human-decision safety
5. add no new prediction or reasoning engine

No new prediction, trend, RUL, diagnosis, threshold, or control engine may be introduced.

**CHANGE DATA, NOT CODE.**