"""ANVIQO durable universal ingestion worker.

Processes queued plant-ingestion jobs for any tenant/plant. No plant-specific
logic is embedded here. CHANGE DATA, NOT CODE.
"""
from __future__ import annotations

import sys


def main() -> int:
    import anvi_plant_ingestion_v2 as ingestion
    try:
        result = ingestion.run_pending_jobs(limit=1)
        print(f"ANVI universal ingestion worker: processed={result.get('processed', 0)}", flush=True)
        return 0
    except Exception as exc:
        print(f"ANVI universal ingestion worker failed: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
