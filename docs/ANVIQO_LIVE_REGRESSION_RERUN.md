# ANVIQO live regression rerun

Run the existing 200-question semantic suite against the live isolated V2-V3 test service after the current answer fixes.

The previous live run failed with 16 blank-answer or semantic failures. Inspect all 200 answer bodies and statuses, especially PT-303 PCI identity, diagnosis and evidence, saved field-report retrieval, historical trend questions, and instrument health. HTTP 200 alone is not a pass.

Do not merge this QA-only branch or deploy to production as part of the rerun. Preserve the frozen V2-V3 certified restore point.