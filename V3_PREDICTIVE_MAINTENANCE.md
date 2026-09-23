# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 11 IMPLEMENTED, PENDING CI VERIFICATION

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
11. **Predictive Outcome Verification Integration** — IMPLEMENTED

## Alpha 10 predictive flow

`v3/predictive_flow.py` is the single orchestration boundary for the V3 predictive path.

It composes the already existing contracts in this order:

evidence validation
-> optional tenant-scoped history
-> optional tenant-scoped maintenance memory
-> predictive context assembly
-> existing tenant-aware predictor
-> prediction-result validation

Alpha 10 was verified by the dedicated V3 regression workflow on commit `7dab9bcf65dfb58cb7d72034e1ae1a9976b67c89`.

It does NOT add a prediction/model engine or calculate:
- failure probability
- trend
- RUL
- diagnosis
- causation
- thresholds
- control actions

A predictor is not invoked when the evidence gate is insufficient, and legacy/global predictors remain blocked.

## Alpha 11 outcome verification integration

Alpha 11 reuses the existing `v3/prediction_outcomes.py` contract instead of creating a second outcome engine.

When an existing tenant-aware predictor is actually invoked and an explicit outcome is supplied, the canonical flow calls `verify_prediction_outcome()`.

Supported states remain the existing contract:
- `VERIFIED_MATCH`
- `VERIFIED_MISMATCH`
- `UNVERIFIED`

No outcome is inferred, and no model training or prediction adjustment is added.

Cross-plant prediction/outcome pairs remain rejected.

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> tenant-safe history/memory where explicitly available
-> canonical predictive context
-> existing predictor only when explicitly tenant-aware
-> canonical prediction-result validation
-> explicit outcome verification when supplied
-> human verification / decision

**CHANGE DATA, NOT CODE.**

## Existing intelligence boundary

Legacy/global `failure_prediction.py`, `failure_prediction_history.py`, `plant_memory.py`, and `pci_plant_memory.py` remain outside V3 integration where they lack explicit tenant contracts.

No legacy/global data is used as a hidden fallback.

## Tenant and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Cross-plant prediction outcome: REJECTED
- Tag mismatch: REJECTED
- Legacy/global predictor: BLOCKED
- Legacy/global history: BLOCKED
- Legacy/global memory: BLOCKED
- Insufficient evidence: predictor NOT INVOKED
- No explicit outcome: outcome NOT inferred
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Alpha 10 dedicated V3 regression: **PASSED**.

Alpha 11 dedicated V3 regression: **PENDING CI**.

The branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

After Alpha 11 CI verification, inspect the existing predictive/maintenance architecture again before selecting the next milestone. Do not duplicate an existing tenant-safe capability.
