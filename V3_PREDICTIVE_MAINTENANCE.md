# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 8 IMPLEMENTED, PENDING CI VERIFICATION

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED
4. **Universal Predictive Evidence Quality & Window Contract** — VERIFIED
5. **Tenant-safe Predictive History Provider Bridge** — VERIFIED
6. **Canonical Tenant-safe Predictor Invocation Path** — VERIFIED
7. **Tenant-safe Maintenance Memory Bridge** — VERIFIED
8. **Canonical Tenant-safe Predictive Context** — IMPLEMENTED

## Alpha 8 predictive context

`v3/predictive_context.py` is a composition boundary for already validated V3 evidence, history, and maintenance-memory results.

It verifies that every supplied context component belongs to the requested `plant_id` and `tag`, then assembles one predictive context object.

It does NOT calculate:
- failure probability
- trend
- RUL
- diagnosis
- causation
- thresholds
- control actions

No second prediction or learning engine is introduced.

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> canonical tenant-safe predictor bridge
-> tenant-safe history/memory where explicitly available
-> canonical predictive context
-> existing predictor only when explicitly tenant-aware
-> explicit outcome verification
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
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Dedicated V3 regression workflow: **PENDING ALPHA 8 CI**

The branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

After Alpha 8 CI verification, inspect the existing predictive/maintenance architecture again before selecting the next milestone. Do not duplicate an existing tenant-safe capability.
