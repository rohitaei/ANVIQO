"""ANVIQO durable universal ingestion worker service.

This process is isolated from the main web worker. It polls the durable
Postgres/SQLite queue and processes one job at a time for any plant/tenant.
No plant-specific logic is embedded here. CHANGE DATA, NOT CODE.
"""
from __future__ import annotations

import os
import threading
import time

from flask import Flask, jsonify

app = Flask(__name__)


def _worker_loop():
    import anvi_plant_ingestion_v2 as ingestion
    while True:
        try:
            result = ingestion.run_pending_jobs(limit=1)
            print(f"ANVI universal ingestion worker: processed={result.get('processed', 0)}", flush=True)
        except Exception as exc:
            print(f"ANVI universal ingestion worker error: {exc}", flush=True)
        time.sleep(20)


@app.get("/health")
def health():
    return jsonify({"status": "OK", "service": "anviqo-universal-ingestion-worker"})


if __name__ == "__main__":
    threading.Thread(target=_worker_loop, daemon=True, name="anvi-ingestion-loop").start()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
