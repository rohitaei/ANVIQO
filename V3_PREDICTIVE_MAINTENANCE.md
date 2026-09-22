# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 3 VERIFIED

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> existing predictor only when explicitly tenant-aware
-> explicit outcome verification
-> human verification / decision

No plant-specific predictive code is created.

## Existing intelligence boundary

The existing `failure_prediction.py` path was inspected before integration. It is a legacy/global path and does not expose an explicit `plant_id` contract. V3 therefore deliberately does NOT connect it.

No prediction logic was copied into V3.

The architecture remains:

**CHANGE DATA, NOT CODE.**

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
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Dedicated V3 regression workflow: **PASS**

Run #17:
- compile: PASS
- predictive maintenance tests: PASS
- predictive bridge tests: PASS
- prediction outcome tests: PASS

The V3 branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

The next milestone is **not** to force-connect the existing global predictor. A tenant-safe real predictor integration can proceed only when an existing prediction implementation exposes a tenant-scoped contract.

Until then, the safe roadmap path is to strengthen universal predictive evidence/outcome handling rather than duplicate or rewrite the existing prediction engine.
