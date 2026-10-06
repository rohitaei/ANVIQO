# ANVIQO V2.0 → V3.0 Unified Release

## Scope

This release composes the complete V2→V3 intelligence path into one universal
runtime facade without plant-specific code forks.

### Included capability domains

1. Real-time normalized telemetry and time-series contract
2. Secure read-only edge ingestion and store-and-forward boundary
3. Alarm and event correlation
4. What Changed with before/after evidence
5. Instrument health and data-quality diagnostics
6. Equipment risk/reliability context
7. Maintenance/spares decision support with human approval
8. Shift intelligence and watch list
9. Energy / production / quality metric foundation
10. Evidence provenance graph
11. Prediction/anomaly validation boundary
12. Causal/root-cause hypothesis boundary
13. Enterprise identity/tenant isolation
14. Audit/governance boundary
15. Digital-twin and optimization boundaries
16. Versioned V3 API facade
17. Mobile/API production-client boundary
18. HA/DR/load/security certification boundary

## Safety

Every route and domain inherits:

- read_only = true
- plc_write = false
- scada_control = false
- automatic_authorization = false
- automatic_execution = false
- human_decision_required = true
- causation_claim = false

## Important production distinction

The repository can validate the universal software contracts in CI. It cannot
truthfully certify a live plant, durable production TSDB, enterprise SSO/MFA,
SIEM, HA/DR, customer OT security review, or Android production release from
code alone.

The remaining path is:

**Simulation → Evidence → Events → What Changed → ANVI → approved read-only PLC edge → PoV → second plant → production certification.**

No PLC/SCADA write path is introduced by this release.
