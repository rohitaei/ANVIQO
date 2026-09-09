# ANVIQO Release Certification V2

Status: READY FOR VALIDATION
Version: ANVIQO-RELEASE-CERTIFICATION-V2
Base: Product V1 launch build

## Purpose

This certification is a non-mutating release-readiness gate for the current ANVIQO architecture.

It verifies, without changing production state:

- active Python source syntax
- required product modules
- 1,064-record PCI integrity and PT-303 identity
- verified-only Plant Memory behavior
- evidence-gated Maintenance Action Memory V1
- Failure Prediction V1.1 separation of production history from simulation/demo data
- frozen PT-303 Failure Prediction Demo safety labeling
- existing conversational Plant Memory recall routes
- API surface and read-only safety boundary
- absence of obvious hard-coded secrets
- absence of mutation operations inside the certification script itself

## Non-negotiable safety

- READ_ONLY: TRUE
- PLC_WRITE: FALSE
- SCADA_CONTROL: FALSE
- AUTOMATIC_EXECUTION: FALSE
- HUMAN_DECISION_REQUIRED: TRUE

## Important boundary

This file does **not** declare that tests, deployment, or production verification have been executed. The certification script must be run in the user's actual project environment before a final production/launch claim is made.

## Architecture rule

The certification layer is audit-only. It does not create another Plant Memory, Maintenance Intelligence, Prediction, Root Cause, or V5 reasoning engine.
