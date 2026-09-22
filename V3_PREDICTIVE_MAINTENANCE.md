# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 4 IMPLEMENTED, PENDING CI VERIFICATION

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED
4. **Universal Predictive Evidence Quality & Window Contract** — IMPLEMENTED

## Alpha 4 evidence quality contract

`v3/predictive_evidence.py` validates supplied predictive observations before any existing predictor is considered. It checks tenant scope, optional tag scope, timestamp validity, numeric value validity, usable/invalid row counts, and the explicit evidence time window. It never repairs missing data or creates predictive conclusions.

The predictive gateway now consumes this canonical evidence-quality result. No new trend, failure probability, RUL, diagnosis, threshold, or control logic was added.

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

Dedicated V3 regression workflow: **PENDING ALPHA 4 CI**

Run #17:
- compile: PASS
- predictive maintenance tests: PASS
- predictive bridge tests: PASS
- prediction outcome tests: PASS

The V3 branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

The next milestone remains tenant-safe integration of an existing predictor only when an existing prediction implementation exposes an explicit tenant-scoped contract. The legacy/global `failure_prediction.py` path remains blocked.
