"""Durable-safe universal ingestion worker entrypoint.

This module intentionally contains no plant-specific reasoning.  It exists so
long-running ingestion can be invoked as a separate process/service instead
of relying on a daemon thread inside the web worker.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    plant_id = (os.environ.get("ANVI_INGEST_PLANT_ID") or "").strip()
    organization_id = (os.environ.get("ANVI_INGEST_ORG_ID") or "").strip()
    if not plant_id or not organization_id:
        print("ANVI ingestion worker requires ANVI_INGEST_PLANT_ID and ANVI_INGEST_ORG_ID", flush=True)
        return 2

    import anvi_plant_ingestion_v2 as ingestion
    ingestion.init_schema()
    # The V2 runtime's durable job implementation is the single source of truth.
    # Execute synchronously so process lifetime owns the job and restarts cannot
    # silently kill an in-process daemon thread.
    actor = {"organization_id": organization_id, "role": "ADMIN", "user_id": "worker"}
    try:
        ingestion.ingest_plant(plant_id, actor)
        return 0
    except Exception as exc:
        print(f"ANVI universal ingestion failed: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
