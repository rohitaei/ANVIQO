# ANVIQO Phase 4 — Advanced Plant Intelligence V1

## Scope
Phase 4 adds a separate, read-only decision-support layer on top of the certified V5, Phase 2 and Phase 3 intelligence. It does not replace or modify frozen reasoning engines.

### Domains
- Energy Intelligence — calculate energy intensity only from supplied energy and production evidence.
- Production Impact Intelligence — quantify explicit production exposure when production evidence exists.
- Safety Intelligence — summarize explicit safety events/interlock/permit evidence; never declare the plant safe.
- AI Maintenance Planner — rank explicit maintenance candidates using risk, criticality and confidence; recommendations only.
- Reliability Intelligence — summarize verified prediction outcomes and recurring verified failure assets.

## Evidence rule
Missing measurements or unverified records produce `INSUFFICIENT_EVIDENCE`. Phase 4 never invents values, events, rates, probabilities, causal claims or plant conditions.

## Safety boundary
`read_only=true`, `plc_write=false`, `scada_control=false`, `human_decision_required=true`, `automatic_authorization=false`, `causation_claim=false`.

No automatic work-order execution, PLC write, SCADA control, or authorization is permitted.

## Integration rule
`build_phase4_snapshot()` is the single aggregation contract. Command Centre/API integration must call this layer with evidence already available from existing ANVIQO services. No new reasoning engine is permitted merely for UI presentation.

## Certification
The initial Phase 4 contract is certified by `test_phase4_advanced_intelligence_v1.py`. Existing Phase 3 and V5 regression suites remain authoritative and must continue to pass before Phase 4 is promoted.
