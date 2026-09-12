Universal ingestion durability repair target:

The web service must not rely on a daemon thread for long-running ingestion. A Render worker restart can leave a durable job stuck at INDEXING and cause the UI to return 429. The execution path must be durable and restart-safe, while remaining tenant-scoped and data-only. Preserve V5 frozen/read-only intelligence, PLC_WRITE=False, SCADA_CONTROL=False, HUMAN_DECISION_REQUIRED=True, and CHANGE DATA, NOT CODE.
