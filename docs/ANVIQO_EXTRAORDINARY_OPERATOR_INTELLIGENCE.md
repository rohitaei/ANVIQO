# ANVIQO Extraordinary Operator/Engineer Intelligence

This release adds one universal evidence-first layer for the 21 extra operator/engineer questions:
attention-now, Plant Time Machine, Plant Story, Plant Memory, anomaly discovery, deterioration,
early warning, recovery, recurring problems, shift handover, historical similarity, simulation what-if,
instrument health, spare intelligence, cost-of-abnormality evidence gate, energy intelligence,
safety intelligence, OT/data trust, and evidence confidence.

All capabilities are tenant-scoped. They do not enable PLC writes, SCADA control, automatic authorization,
or automatic execution. Causal conclusions remain blocked unless supported by evidence and human review.

The existing frozen V2 179-question checkpoint and V1 production branch are not modified by this release.
The 21 questions are additive and should be appended to the existing 179-question runner for a 200-question
combined conversational regression. The repository contains the deterministic contract tests for the new pack;
the live 200-question conversational test still requires the local runner because the 179-question runner is
stored in the user's Termux workspace.
