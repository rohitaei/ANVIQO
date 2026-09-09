# ANVIQO Failure Prediction Demo V1 Freeze

Status: FROZEN
Version: ANVIQO-FP-DEMO-DASHBOARD-V1.0
Date: 2026-09-09

## Scope

The Command Centre Predictive Intelligence page now exposes a dedicated PT-303 Failure Prediction Demo panel at runtime. The existing `anviqo_dashboard.html` source is not modified; the panel is injected by `failure_prediction_dashboard_runtime.py` through the production entrypoint.

## Demo data boundary

- Dataset: `database/failure_prediction/demo/pt303_demo_telemetry.csv`
- Source: `SIMULATION`
- PT-303 observations: 8
- First value: 48.2 kg/cm²
- Last value: 53.7 kg/cm²
- Delta: +5.5 kg/cm²
- Direction: RISING
- Failure probability: not calculated
- Failure date: not calculated

## Safety boundary

- Production prediction history write: BLOCKED
- PLC write: BLOCKED
- SCADA control: BLOCKED
- Automatic execution: BLOCKED
- Human decision: REQUIRED
- Synthetic/demo observations must never enter production prediction history.

## Validation

Regression coverage includes:

- Demo loader validation
- Demo prediction contract
- Trend-point output for visualization
- Dashboard injection contract and idempotency
- Python compilation in GitHub Actions workflow

GitHub Actions status is not asserted here because no workflow run/status was available at freeze time.

## Frozen rule

This demo layer is presentation and simulation support only. Real plant prediction must use authorized, provenance-labelled, non-simulation observations through the existing Failure Prediction history boundary.
