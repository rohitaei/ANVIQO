# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 10 IMPLEMENTED, PENDING CI VERIFICATION

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
10. **Canonical Predictive Flow Boundary** — IMPLEMENTED

## Alpha 10 predictive flow

`v3/predictive_flow.py` is the single orchestration boundary for the V3 predictive path.

It composes the already existing contracts in this order:

evidence validation
-> optional tenant-scoped history
-> optional tenant-scoped maintenance memory
-> predictive context assembly
-> existing tenant-aware predictor
-> prediction-result validation

It does NOT add a prediction/model engine or calculate:
- failure probability
- trend
- RUL
- diagnosis
- causation
- thresholds
- control actions

A predictor is not invoked when the evidence gate is insufficient, and legacy/global predictors remain blocked.

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> tenant-safe history/memory where explicitly available
-> canonical predictive context
-> existing predictor only when explicitly tenant-aware
-> canonical prediction-result validation
-> human verification / decision

**CHANGE DATA, NOT CODE.**

## Existing intelligence boundary

Legacy/global `failure_prediction.py`, `failure_prediction_history.py`, `plant_memory.py`, and `pci_plant_memory.py` remain outside V3 integration where they lack explicit tenant contracts.

No legacy/global data is used as a hidden fallback.

## Tenant and safety guarantees

- Cross-plant evidence: REJECTED
- Cross-plant history: REJECTED
- Cross-plant maintenance memory: REJECTED
- Tag mismatch: REJECTED
- Legacy/global predictor: BLOCKED
- Legacy/global history: BLOCKED
- Legacy/global memory: BLOCKED
- Insufficient evidence: predictor NOT INVOKED
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Dedicated V3 regression workflow: **PENDING ALPHA 10 CI**

The branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

After Alpha 10 CI verification, inspect the existing predictive/maintenance architecture again before selecting the next milestone. Do not duplicate an existing tenant-safe capability.
