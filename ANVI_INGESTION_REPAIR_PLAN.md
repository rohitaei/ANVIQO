# Universal ingestion repair

Long-running ingestion must not depend on a daemon thread inside the Render web worker. Jobs must be restart-safe and tenant-scoped. Preserve V5 frozen/read-only intelligence, PLC_WRITE=False, SCADA_CONTROL=False, HUMAN_DECISION_REQUIRED=True, and CHANGE DATA, NOT CODE.
