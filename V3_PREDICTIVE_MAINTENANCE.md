# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 6 IMPLEMENTED, PENDING CI VERIFICATION

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED
4. **Universal Predictive Evidence Quality & Window Contract** — VERIFIED
5. **Tenant-safe Predictive History Provider Bridge** — VERIFIED
6. **Canonical Tenant-safe Predictor Invocation Path** — IMPLEMENTED

## Alpha 6 canonical predictor gateway

`v3/predictive_maintenance.py` remains the evidence/request front door, but it no longer contains a second predictor-invocation implementation. Its `run_existing_predictor()` compatibility entry point delegates to `v3.predictive_bridge.invoke_existing_predictor()`.

This removes duplicate predictor invocation logic while preserving the existing public entry point.

The canonical bridge requires an explicit `plant_id` parameter on any supplied predictor. Legacy/global predictors remain blocked.

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> canonical tenant-safe predictor bridge
-> existing predictor only when explicitly tenant-aware
-> explicit outcome verification
-> human verification / decision

No plant-specific predictive code is created.

## Existing intelligence boundary

The existing `failure_prediction.py` path was inspected before integration. It is a legacy/global path and does not expose an explicit `plant_id` contract. V3 therefore deliberately does NOT connect it.

No prediction logic was copied into V3.

The architecture remains:

**CHANGE DATA, NOT CODE.**

## Predictive history boundary

`v3/predictive_history_bridge.py` accepts historical observations only from an explicitly tenant-scoped provider. The existing `failure_prediction_history.py` remains outside the bridge because its records do not expose explicit `plant_id`.

## Outcome verification

V3 accepts explicit prediction and actual outcome records and returns:

- `VERIFIED_MATCH`
- `VERIFIED_MISMATCH`
- `UNVERIFIED`

It does not infer outcomes, train models, calculate RUL/probabilities, diagnose failures, or control equipment.

## Tenant and safety guarantees

- Cross-plant predictive evidence: REJECTED
- Cross-plant outcomes: REJECTED
- Legacy/global predictor: BLOCKED
- Legacy/global history: BLOCKED
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Dedicated V3 regression workflow: **PENDING ALPHA 6 CI**

The branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

After Alpha 6 CI verification, the next milestone will be selected only after inspecting the existing predictive/maintenance architecture for an already-supported tenant-scoped integration point. No legacy/global prediction path will be forced into V3.
