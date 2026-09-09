# ANVIQO Phase 3 — Critical Spare Intelligence V2

## Status
COMPLETE — implemented on top of the Phase 2 field-report runtime.

## Objective
Make critical-spare inventory operationally authoritative while preserving the ANVIQO safety boundary.

## V2 contract
- `database/spares/critical_spares.xlsx` is the authoritative current inventory.
- Explicit ADD / RECEIVED commands increase stock directly.
- Explicit USED / REMOVE / CONSUMED commands decrease stock directly.
- Ordinary spare questions remain read-only.
- A spare mention alone never changes inventory.
- Inventory can never become negative.
- Every successful direct mutation records before/after quantity and a transaction ID.
- Field-report explicit spare use is synchronized exactly once per Plant Memory report ID.
- Later spare queries read the updated authoritative workbook.
- Inventory mutations require `inventory:write` permission at the Phase 2 API boundary.
- No PLC write and no SCADA control.
- V5 intelligence modules remain frozen.

## End-to-end acceptance flow
1. Ask ANVI for the current quantity of a known spare.
2. Issue an explicit add/receive command.
3. Verify the workbook quantity increases and the response reports before/after.
4. Ask ANVI for the spare again and verify the updated quantity.
5. Issue an explicit used/consumed command.
6. Verify the workbook quantity decreases and the response reports before/after.
7. Replay the same field report and verify no second decrement occurs.
8. Attempt a removal larger than available and verify the operation is rejected.
9. Verify a read-only mention such as “PT-303 spare is available” does not mutate stock.
10. Verify all existing Phase 2 and V5 freeze tests remain green.
