# ANVIQO V3 - Predictive Maintenance Foundation

Status: V3 PREDICTIVE MAINTENANCE — ALPHA 7 IMPLEMENTED, PENDING CI VERIFICATION

## Completed milestones

1. **Universal Predictive Evidence Gateway** — VERIFIED
2. **Tenant-safe Existing Predictor Bridge** — VERIFIED
3. **Explicit Prediction Outcome Verification Contract** — VERIFIED
4. **Universal Predictive Evidence Quality & Window Contract** — VERIFIED
5. **Tenant-safe Predictive History Provider Bridge** — VERIFIED
6. **Canonical Tenant-safe Predictor Invocation Path** — VERIFIED
7. **Tenant-safe Maintenance Memory Bridge** — IMPLEMENTED

## Alpha 7 maintenance memory boundary

`v3/maintenance_memory_bridge.py` provides a universal retrieval seam for existing maintenance memory. It accepts records only from a provider that explicitly declares `plant_id`.

Returned records must carry the requested plant scope. If a tag is present, it must match the requested tag.

The existing `plant_memory.py` and `pci_plant_memory.py` implementations were inspected and remain outside this bridge because they do not expose an explicit tenant contract. V3 does not silently consume their global records.

This milestone adds no new learning or reasoning engine. It is retrieval orchestration only.

## Universal contract

Any plant
-> tenant-scoped observations
-> predictive evidence validation
-> canonical tenant-safe predictor bridge
-> tenant-safe maintenance memory when explicitly available
-> existing predictor only when explicitly tenant-aware
-> explicit outcome verification
-> human verification / decision

No plant-specific predictive code is created.

## Existing intelligence boundary

The existing `failure_prediction.py` path remains blocked because it is legacy/global and does not expose explicit `plant_id`.

The existing `failure_prediction_history.py` path remains outside V3 for the same tenant-scope reason.

No prediction, trend, probability, RUL, diagnosis, causation, or control logic was copied into V3.

## Tenant and safety guarantees

- Cross-plant predictive evidence: REJECTED
- Cross-plant outcomes: REJECTED
- Cross-plant maintenance memory: REJECTED
- Legacy/global predictor: BLOCKED
- Legacy/global history: BLOCKED
- Legacy/global maintenance memory: BLOCKED
- Read-only: TRUE
- PLC write: FALSE
- SCADA control: FALSE
- Automatic action: FALSE
- Human decision required: TRUE

## Verification

Dedicated V3 regression workflow: **PENDING ALPHA 7 CI**

The branch remains separate and PR #40 remains draft/unmerged.

## Next milestone

After Alpha 7 CI verification, inspect the existing architecture again before selecting the next milestone. Do not create duplicate prediction or learning logic where an existing tenant-safe contract already exists.
