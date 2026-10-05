# ANVIQO Global V2 Certification Plan

## Gate 0 — frozen baseline
Verify V1 production remains unchanged and the freeze branch remains recoverable.

## Gate 1 — tenant isolation
Two organizations and two plants:
- own evidence visible
- foreign evidence invisible
- foreign evidence never used as fallback
- new plant works without plant-specific code

## Gate 2 — evidence
Verify provenance, timestamps, quality, source and selected-plant ownership.

## Gate 3 — real-time
Test reconnect, buffering, duplicate observations, stale data and clock skew.

## Gate 4 — intelligence
Test health, alarms, events, what changed, diagnosis, prediction, maintenance and learning against known evidence.

## Gate 5 — safety
Prove every action path remains read-only and human-gated.

## Gate 6 — security
Authentication, authorization, session isolation, secrets, audit, rate limiting and dependency/security checks.

## Gate 7 — scale
Load test tenants/plants/tags/events and establish latency/error budgets.

## Gate 8 — resilience
Restart, database failure, edge disconnect, cloud restart, backup restore and disaster recovery.

## Gate 9 — plant PoV
Simulation -> evidence -> events -> what changed -> ANVI -> approved read-only PLC -> PoV -> second plant.

No production/global certification is granted until all gates pass.
