# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 15 IMPLEMENTED, PENDING CI VERIFICATION

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
15. **Complete Real Evidence Context Composition** — IMPLEMENTED, PENDING CI

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

### Next safe milestone

**Alpha 12 — Tenant-safe integration of the existing predictor**

This milestone must adapt the existing predictor's real intelligence to explicit tenant-scoped evidence **without duplicating its prediction logic**.

Required before implementation:
1. identify every data source used by the existing predictor
2. establish an explicit `plant_id` contract for each required source
3. preserve existing prediction logic rather than copy it into `v3/`
4. add cross-plant rejection tests
5. verify read-only/human-decision safety
6. run dedicated V3 CI before declaring Alpha 12 verified

If a required source cannot be made tenant-safe, V3 will keep that path blocked rather than silently falling back to global data.

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

The branch remains separate and PR #40 remains draft/unmerged.
