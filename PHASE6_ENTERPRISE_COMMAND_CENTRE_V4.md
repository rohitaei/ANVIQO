# ANVIQO Phase 6 Enterprise Command Centre V4

## Purpose

Adds real tenant-scoped plant-context switching to the Enterprise Command Centre.

## Behavior

- Authorized users can select a plant within their active organization.
- Tenant admins may switch to any plant in their organization.
- Non-admin users must hold `plant:read` membership for the selected plant.
- Cross-organization plants are always rejected.
- The selected plant is stored in the authenticated session context.
- A context-switch audit record is attempted through the existing tenant audit contract.
- Existing V5/V5.7 intelligence is reused; no new reasoning engine is introduced.

## Evidence contract

A context switch changes **context**, not plant facts. Existing intelligence is only attributed to a selected plant when the underlying evidence contract provides plant-scoped evidence. Missing plant-scoped evidence must remain `NOT_EVALUATED` or `INSUFFICIENT_EVIDENCE`; ANVIQO must not fabricate health, risk, production, energy, reliability, or event facts.

## API

- `POST /api/enterprise/select-plant` — select an authorized plant context.
- `GET /api/enterprise/active-context` — return the current organization/plant context.
- `GET /api/enterprise/portfolio` — portfolio view follows the selected active plant.

## Safety

`plc_write=false`, `scada_control=false`, `automatic_authorization=false`, `automatic_execution=false`, `human_decision_required=true`.

This phase is governance/context only. It does not enable PLC/SCADA writes or automatic execution.
