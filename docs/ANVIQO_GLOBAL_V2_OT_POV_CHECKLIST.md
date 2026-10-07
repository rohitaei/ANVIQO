# ANVIQO Global V2 — OT PoV Acceptance Checklist

## A. Plant and network
- [ ] Plant, organization and area identity confirmed.
- [ ] Read-only edge gateway approved by plant OT/IT.
- [ ] Outbound-only network path approved.
- [ ] No inbound cloud-to-PLC control path.
- [ ] Firewall/segmentation rules documented.
- [ ] Clock/time synchronization verified.

## B. Data
- [ ] Required tags and engineering units mapped.
- [ ] Quality/state semantics defined.
- [ ] UTC timestamps verified.
- [ ] Sequence/reconnect behavior verified.
- [ ] Store-and-forward behavior tested.
- [ ] Duplicate observations do not create duplicate evidence.

## C. Intelligence
- [ ] What Changed traceable to source observations/events.
- [ ] Event correlation tested on real PoV data.
- [ ] ANVI answers cite plant evidence.
- [ ] Prediction/anomaly outputs have validation metrics.
- [ ] Causal hypotheses remain hypotheses and require human review.
- [ ] Maintenance recommendations are human-reviewed.

## D. Safety
- [ ] read_only=True
- [ ] plc_write=False
- [ ] scada_control=False
- [ ] automatic_authorization=False
- [ ] automatic_execution=False
- [ ] human_decision_required=True

## E. Security and governance
- [ ] Tenant isolation tested.
- [ ] User/RBAC boundary approved.
- [ ] Authentication/MFA/SSO plan approved where required.
- [ ] Audit records retained.
- [ ] Secrets are not stored in telemetry/evidence payloads.
- [ ] Incident and rollback procedure documented.

## F. Outcome
- [ ] Baseline KPI recorded before PoV.
- [ ] Post-PoV KPI recorded.
- [ ] False-positive/false-negative behavior reviewed.
- [ ] Operator acceptance recorded.
- [ ] Second-plant repeatability plan approved.

A checklist item is not considered passed merely because a software contract exists; external plant evidence is required for live/certification gates.
