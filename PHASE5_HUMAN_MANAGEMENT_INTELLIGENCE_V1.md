# ANVIQO Phase 5 — Human & Management Intelligence V1

## Status
Foundation implementation complete on the Phase 5 branch. This layer is intentionally separate from frozen V5 and released Phase 4 intelligence.

## Audit finding
Existing V5 already contains Shift Intelligence, Management Intelligence, Decision Intelligence, and V5.7 Executive/HOD Intelligence. Therefore Phase 5 does **not** recreate those reasoning engines. The new layer is the management-facing orchestration and human-governance contract around their verified outputs.

## Capabilities
- Management brief: concise plant situation, health, priorities, changes and shift context.
- Human action queue: converts existing priorities into reviewable human follow-up items.
- Human decision record: records APPROVE / REJECT / DEFER / ACKNOWLEDGE decisions without executing work.
- Evidence-aware state: empty evidence is explicitly `INSUFFICIENT_EVIDENCE`.
- Reuses existing V5/Phase 4 outputs; no independent plant reasoning or fabricated values.

## Governance
- `read_only=true`
- `plc_write=false`
- `scada_control=false`
- `automatic_authorization=false`
- `automatic_execution=false`
- `human_decision_required=true`
- `causation_claim=false`

An APPROVE decision is a recorded human decision, not permission for ANVIQO to execute PLC/SCADA or maintenance actions.

## Test contract
`test_phase5_human_management_intelligence_v1.py` covers insufficient evidence, priority reuse, non-executing action queue, human decision recording, invalid decisions, and safety boundary.

## Next integration
After foundation certification, integrate this contract into the Command Centre without replacing the existing V5/Phase 4 reasoning stack. Management/HOD presentation must remain evidence-backed and must never imply automatic authorization or execution.
