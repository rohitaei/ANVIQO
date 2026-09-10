# ANVIQO Phase 6 Enterprise Context Propagation V5

## Purpose
Propagate the authenticated organization and selected plant context consistently to enterprise API surfaces without changing frozen V5 reasoning.

## Contract
- `ANVIQO-PLANT-CONTEXT-V1`
- Organization comes from the authenticated tenant session.
- Active plant comes from the authenticated session after V4 plant selection.
- API responses expose the active context through `X-ANVIQO-*` headers.
- `/api/enterprise/context-envelope?surface=...` exposes the canonical context envelope for Chat, Management, Plant Health, Events, and Reports.
- `/api/enterprise/context-check` verifies whether a plant identifier matches the active session context.

## Evidence rule
Context selection is not evidence. Existing intelligence may only be attributed to a selected plant when the evidence is demonstrably bound to that plant. Otherwise the surface must report `NOT_EVALUATED` or `INSUFFICIENT_EVIDENCE`.

## Safety
No PLC write, SCADA control, automatic authorization, or automatic execution is introduced. Human decision remains required. Frozen V5 intelligence is not modified.

## Freeze gate
V5 is accepted only after context propagation tests, tenant regression, compile checks, and safety checks pass.
