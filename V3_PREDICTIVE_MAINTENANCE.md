# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE FOUNDATION STARTED

## Purpose

V3 begins the predictive-maintenance/futurecast phase without replacing or duplicating existing ANVIQO prediction intelligence.

The first milestone is the **Universal Predictive Evidence Gateway**.

## Contract

Any plant can provide timestamped equipment observations through the same contract:

Any Plant
-> tenant-scoped observations
-> predictive evidence validation
-> existing predictor (when explicitly supplied)
-> human verification / decision

The gateway does not contain plant-specific thresholds, failure rules, probabilities, failure dates, or control actions.

## Evidence gate

A prediction request is marked READY_FOR_EXISTING_PREDICTOR only when at least two timestamped numeric observations are available.

With insufficient evidence:

- prediction is not invoked
- no future failure is inferred
- the reason is returned explicitly

Cross-plant evidence is rejected.

## Existing intelligence boundary

The gateway is deliberately an orchestration layer. It does not copy or rewrite `failure_prediction.py`.

An existing predictor may be injected only after tenant/evidence validation. If no predictor is supplied, the gateway returns NOT_INVOKED rather than creating replacement prediction logic.

This preserves the architecture principle:

**CHANGE DATA, NOT CODE.**

## Safety

- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

`tests/test_v3_predictive_maintenance.py` covers:

- tenant-scoped evidence
- cross-plant rejection
- insufficient-evidence gating
- invocation only of an explicitly supplied predictor
- read-only/human-governed safety

The dedicated GitHub Actions workflow is `.github/workflows/v3-predictive-maintenance.yml`.

## Next V3 milestone

After this evidence gateway is verified, the next milestone can connect the gateway to an existing prediction path in a tenant-safe manner and then add prediction verification/outcome learning without creating a second prediction engine.
