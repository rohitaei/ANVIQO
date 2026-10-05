# ANVIQO Global V2 — 30-Day End-to-End Simulation Runbook

This campaign exercises the V2 contracts using two isolated synthetic plants over 30 calendar days. It is the strongest software-level soak test available without connecting customer OT hardware.

## Simulated problems
- PT_303 pressure excursions on days 10–11.
- Bad-quality telemetry window on day 17.
- Edge reconnect and duplicate telemetry on days 6 and 20.
- Alarm/state-change events.
- Evidence replay and graph generation.
- Prediction outcome/MAE validation, anomaly scoring and drift checks.
- Evidence-backed causal hypotheses that remain human-review-only.
- Digital twin and what-if simulation.
- CMMS dry-run integration.
- Deliberate S7 write attempt, which must fail closed.
- Deliberate cross-tenant access attempts, which must fail closed.
- Append-only audit records.
- Simulated resilience, restart and backup/restore drills.
- Plant and consolidated management report generation.

## Acceptance
Telemetry, deduplication, data quality, events, replay, correlation, prediction validation, anomaly/drift, causal boundary, twin/what-if, enterprise dry-run, OT write blocking, tenant isolation, audit, resilience, safety and PoV gates must all pass.

## Run
Run the module with Python to print the complete JSON result. The harness also provides a function to write the report to reports/ANVIQO_V2_30_DAY_SIMULATION_REPORT.json.

## Important limitation
A 30-day simulation proves software behavior under modeled conditions. It does not prove live Siemens S7/OPC UA/MQTT/Sparkplug/Modbus connectivity, plant network/security approval, production HA/DR, real model accuracy, or customer operational outcomes. Production certification remains an external evidence gate.
