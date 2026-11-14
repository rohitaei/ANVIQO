# ANVIQO Universal Plant Data Workbook

Download: `ANVIQO_Universal_Plant_Data_Template.xlsx`

Use the same workbook structure for every plant. Fill only the tabs relevant to the site and leave unknown values blank. The ingestion pipeline preserves source rows and joins alarm limits and digital semantics to matching instrument tags.

## Workbook tabs

- `Plant_Profile`: plant identity, industry, timezone and data mode.
- `Equipment`: equipment hierarchy, area, type, criticality and identity.
- `Instruments_IO`: tag, service, I/O type, PLC address, panel, terminals, make/model, range, units and configuration approval.
- `Alarm_Limits`: one row per alarm limit; link by exact tag; include class, direction, setpoint, unit, delay, deadband and operator response.
- `Digital_Semantics`: explicit normal and alarm states for DI/DO; never assume polarity.
- `Spares`: spare part master and verified stock quantity.
- `Spare_Compatibility`: map spare IDs to exact tags/equipment and required quantities.
- `Maintenance_History`: field observations, findings, actions, spare usage, outcomes and verification status.
- `Field_Guide`: field definitions and rules; informational only.

## Configuration status

- `DEMO_ONLY`: illustrative profile; may be used only when the instrument row is explicitly `SIMULATION`. Results remain synthetic and are labelled as a demo profile, not engineering approval.
- `PENDING_REVIEW`: imported but not assessed against limits.
- `APPROVED`: usable for operational engineering assessment only when an authorized approver and approval reference are present on the instrument row and each linked alarm limit row.
- `REJECTED`: never used for assessment.

## Import rules

1. Use one stable tag per physical signal. Use `equipment_id` to connect instruments to equipment.
2. Alarm limits must reference the exact tag and use the same engineering unit as the instrument range.
3. Analog assessment requires a valid range plus all four bounds: warning low/high and critical low/high.
4. Digital assessment requires explicit normal and alarm states, with no overlap.
5. Unknown values stay blank and remain unassessed. ANVIQO must not infer engineering limits.
6. Spare quantities are inventory inputs; field reports do not automatically deduct stock.
7. Trip action is informational only. This workbook never enables PLC writes, SCADA control, automatic trips or automatic authorization.
8. Preserve source file and approval references for audit.

The sample PT_303 and spare records in the workbook are deliberately fictional, use `DEMO_ONLY`, and must not be copied into a live plant configuration.
