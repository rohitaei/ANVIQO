# ANVIQO Phase 6 Enterprise Command Centre V3

## Scope

Adds the first enterprise portfolio roll-up without inventing cross-plant intelligence.

- Organization-scoped plant portfolio
- All authorized plant metadata visible to the tenant
- Existing live evidence reused only for the authenticated active plant
- Other plants explicitly marked `NOT_EVALUATED` until a real plant-context switch/evidence contract exists
- No duplicate reasoning engine

## Safety

`plc_write=false`, `scada_control=false`, `automatic_authorization=false`, `automatic_execution=false`, `human_decision_required=true`.

## Freeze gate

Do not calculate enterprise health, risk, production, energy, or reliability KPIs from missing plant evidence. Every aggregate must identify its evidence scope.
