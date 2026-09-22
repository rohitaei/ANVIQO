# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE FOUNDATION — ALPHA 3 COMPLETE

## Purpose

V3 continues the predictive-maintenance/futurecast phase without replacing or duplicating existing ANVIQO prediction intelligence.

Completed milestones:

1. **Universal Predictive Evidence Gateway**
2. **Tenant-safe Existing Predictor Bridge**
3. **Explicit Prediction Outcome Verification Contract**

## Universal contract

Any plant can provide timestamped equipment observations through the same contract:

Any Plant
-> tenant-scoped observations
-> predictive evidence validation
-> existing predictor (only when explicitly tenant-aware)
-> explicit outcome verification
-> human verification / decision

The V3 foundation does not contain plant-specific thresholds, failure rules, probabilities, failure dates, RUL logic, diagnosis, or control actions.

## Evidence gate

A prediction request is marked READY_FOR_EXISTING_PREDICTOR only when at least two timestamped numeric observations are available.

With insufficient evidence:

- prediction is not invoked
- no future failure is inferred
- the reason is returned explicitly

Cross-plant evidence is rejected.

## Existing intelligence boundary

The gateway and bridge are orchestration layers. They do not copy or rewrite `failure_prediction.py`.

An existing predictor may be invoked only when it explicitly declares `plant_id`. Legacy/global predictors are blocked because they may read non-tenant-scoped data.

This preserves the architecture principle:

**CHANGE DATA, NOT CODE.**

## Outcome verification

`v3/prediction_outcomes.py` accepts only explicit prediction and outcome records.

It:

- requires matching tenant and tag
- returns UNVERIFIED when comparable states are not explicitly supplied
- records VERIFIED_MATCH or VERIFIED_MISMATCH when both states are explicit
- does not infer an outcome
- does not train a model
- does not modify the existing predictor
- provides a future seam for verified outcome learning

No duplicate prediction engine was created.

## Safety

- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

The dedicated GitHub Actions workflow is `.github/workflows/v3-predictive-maintenance.yml`.

It now compiles and runs:

- `tests/test_v3_predictive_maintenance.py`
- `tests/test_v3_predictive_bridge.py`
- `tests/test_v3_prediction_outcomes.py`

V3 Alpha 2 was verified successfully after its test assertion fix. Alpha 3 is being verified by the updated regression workflow before any further milestone is started.

## Roadmap discipline

No V3 milestone will be skipped, duplicated, or implemented ahead of verification.

The next milestone after Alpha 3 verification is **tenant-safe integration with a real existing prediction path**, but only if an existing predictor can consume tenant-scoped evidence without global/PCI fallback. Otherwise the integration remains explicitly blocked rather than creating duplicate prediction logic.
