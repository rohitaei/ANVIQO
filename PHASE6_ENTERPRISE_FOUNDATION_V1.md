# ANVIQO Phase 6 — Enterprise Foundation V1

## Purpose

Extend the existing Phase 2 tenant foundation into a safe enterprise plant control plane without changing frozen V5 intelligence.

## V1 scope

- organization-scoped plant directory
- authenticated enterprise context
- tenant-admin plant creation
- plant-level read authorization
- explicit governance/safety contract
- cross-organization isolation
- audit remains supplied by the existing Phase 2 tenant layer

## Architecture

Existing authentication + tenant authorization → Phase 6 enterprise adapter → existing V5/Phase 5 intelligence.

No second reasoning engine is introduced.

## Safety

- read-only intelligence: true
- PLC write: false
- SCADA control: false
- automatic authorization: false
- automatic execution: false
- human decision required: true

## Non-goals

V1 does not add automatic control, autonomous work orders, a second plant-health engine, or fabricated enterprise KPIs.

## Freeze gate

Phase 6 V1 is frozen only after enterprise, tenant-regression, compile, and safety tests pass on the release branch.
