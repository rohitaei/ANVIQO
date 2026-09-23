# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 20 IMPLEMENTED, PENDING CI VERIFICATION

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
20. **Predictive Flow Production Boundary Inspection** — IMPLEMENTED, PENDING CI

## Alpha 11 outcome verification integration

Alpha 11 reuses the existing `v3/prediction_outcomes.py` contract inside the canonical `v3/predictive_flow.py` boundary.

When an existing tenant-aware predictor is invoked and an explicit outcome is supplied, the existing verification contract is reused.

Supported states remain:
- `VERIFIED_MATCH`
- `VERIFIED_MISMATCH`
- `UNVERIFIED`

No outcome is inferred, no model training is added, and no prediction is modified from an outcome.


## Alpha 12 tenant-safe existing predictor integration

Alpha 12 adds a tenant-scoped source contract for every data source consumed by the existing prediction algorithm:
- PCI identity/live evidence
- persisted predictive history
- verified maintenance memory
- event timeline
- equipment health

v3/predictive_sources.py requires every provider to explicitly declare plant_id and rejects rows whose plant_id or tag does not match the requested tenant.

failure_prediction.py now exposes build_tenant_failure_prediction(...), which reuses the existing prediction/trend implementation after receiving validated tenant-scoped source data. The legacy build_failure_prediction(...) entry point remains unchanged for existing callers and is not used by V3.

v3/existing_predictor_adapter.py connects this tenant-safe entry point to the existing V3 predictor bridge. No prediction algorithm was copied into v3/.

Alpha 12 tests cover:
- existing trend behavior through tenant-scoped sources
- tenant-aware adapter invocation
- cross-plant source rejection
- legacy provider rejection

## Architecture inspection after Alpha 11

The existing `failure_prediction.py` contains real prediction/trend logic, so V3 must NOT copy or recreate it.

However, the existing predictor is currently legacy/global:
- its public `build_failure_prediction()` entry point does not declare `plant_id`
- its supporting PCI/history/memory/event sources are not uniformly tenant-scoped
- V3 therefore correctly blocks it through the existing tenant-safe predictor bridge

This is an intentional safety boundary, not a missing fallback.

### Alpha 19 predictive execution provenance contract

Alpha 19 adds a deterministic provenance record to the canonical predictive flow.

The contract captures:
- exact plant and tag scope
- evidence quality and observation/window summary
- context assembly status
- predictor invocation status/reason
- explicit outcome-verification status
- immutable safety flags

The audit object is a contract builder only. It does not persist records, calculate predictions, interpret predictor output, infer outcomes, or perform control actions. Persistence remains the caller's responsibility.

### Next safe milestone

**Alpha 20 — Predictive Flow Production Boundary Inspection**

Before adding another feature, inspect the complete V3 package-flow path against the real application boundary and identify any remaining integration gap between the verified tenant-safe predictive foundation and the user-facing Predictive Intelligence path.

Required before implementation:
1. trace the actual production entry point into the canonical package flow
2. verify tenant identity reaches the flow without global fallback
3. verify evidence/window/result provenance survives the API/UI boundary
4. add only missing integration wiring; do not duplicate prediction/trend/RUL/diagnosis logic
5. preserve read-only/human-decision safety
6. run dedicated V3 CI and the relevant application regression checks

No future-state inference, failure probability, RUL, diagnosis, threshold, or control action may be added.

**CHANGE DATA, NOT CODE.**

## Alpha 13 real tenant-scoped evidence providers

Alpha 13 replaces the previous fake-provider-only verification with a real provider set backed by the normalized V1 onboarding package.

`v3/tenant_predictive_providers.py` reads only records belonging to the package's explicit `plant_id` and exposes tenant-scoped providers for:
- PCI identity/live evidence
- predictive history
- maintenance memory
- event timeline
- equipment health

Every predictive evidence row must carry the same explicit `plant_id`; cross-plant requests and missing tenant identity are rejected.

The legacy global stores (`failure_prediction_history.py`, `plant_memory.py`, `pci_plant_memory.py`, `event_timeline.py`, `equipment_health.py`) are deliberately NOT read by this provider. They do not currently carry a reliable tenant contract, so V3 does not relabel their global records as tenant data.

This preserves the universal architecture: plant-specific data enters through the normalized onboarding package, while the existing prediction intelligence remains unchanged.

## Alpha 14 canonical predictive flow from universal plant package

Alpha 14 wires the real Alpha 13 tenant-scoped provider set into the canonical V3 predictive flow.

`v3/predictive_package_flow.py`:
- requires the requested `plant_id` to match the onboarding package tenant
- creates the real tenant-scoped evidence providers
- connects them to the existing predictor through `v3/existing_predictor_adapter.py`
- reuses the canonical V3 predictive flow
- does not add prediction or trend logic

The existing `failure_prediction.py` algorithm remains the single prediction implementation. No legacy/global source is used by this path.

## Alpha 15 complete real evidence context composition

Alpha 15 closes the remaining wiring gap in the canonical package flow.

The real Alpha 13 providers are now passed into the canonical V3 flow for:
- predictive history
- verified maintenance memory

Therefore the canonical predictive context is populated from the same tenant-scoped package sources used by the existing predictor, rather than leaving history and maintenance context as `NOT_PROVIDED`.

No prediction logic is added and no second evidence store is introduced.

## Alpha 17 predictive trust/freshness decision boundary

Alpha 17 makes the existing predictive evidence quality contract an explicit deterministic gate before predictor invocation.

The canonical request is now predictive-ready only when:
- evidence quality is `VALID`
- at least two usable timestamped numeric observations exist

`PARTIAL` evidence remains evidence for reporting but does not authorize predictor invocation, even when it contains two or more usable rows. `EMPTY` evidence is also blocked.

No new trust engine, prediction logic, trend logic, RUL, probability, diagnosis, threshold, or control action was added. The existing predictor remains unchanged and the tenant/read-only boundary remains enforced.

## Alpha 18 predictive evidence freshness window contract

Alpha 18 adds an explicit, caller-supplied evidence window contract using the existing predictive evidence validator.

The contract records the requested `window_start` and `window_end` and rejects an invalid reversed window. Observations outside a supplied window are reported as invalid rather than repaired or silently accepted. The resulting `window_status` is exposed as `VALID`, `PARTIAL`, or `EMPTY`.

The contract is deterministic and timestamp-based. It does not invent a freshness threshold, compare against wall-clock time, or add prediction/trend/RUL/diagnosis/control logic. Predictor invocation remains governed by the Alpha 17 `VALID` evidence boundary.

## Universal and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Cross-plant prediction outcome: REJECTED
- Legacy/global predictor: BLOCKED until tenant-safe
- Legacy/global history: BLOCKED
- Legacy/global memory: BLOCKED
- Insufficient evidence: predictor NOT INVOKED
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
Alpha 20 dedicated V3 regression: **PENDING** on the current branch head.

The branch remains separate and PR #40 remains draft/unmerged.
