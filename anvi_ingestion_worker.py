"""ANVIQO durable universal ingestion worker.

The worker shares the persistent tenant database with the web service and
executes one queued V4 job at a time. No daemon thread in the web process and
no in-memory job state are used for ingestion execution. CHANGE DATA, NOT CODE.
"""
from __future__ import annotations

import threading
import time
from flask import Flask, jsonify

app = Flask(__name__)


def _process_once():
    import anvi_plant_ingestion_v2 as ingestion
    return ingestion.process_one()


def _worker_loop():
    while True:
        try:
            result = _process_once()
            print(
                f"ANVI universal ingestion worker: processed={result.get('processed', 0)} "
                f"job={result.get('job_id', '-')}",
                flush=True,
            )
        except Exception as exc:
            print(f"ANVI universal ingestion worker error: {exc}", flush=True)
        time.sleep(5)


@app.get("/health")
def health():
    return jsonify({"status": "OK", "service": "anviqo-universal-ingestion-worker"})


if __name__ == "__main__":
    threading.Thread(target=_worker_loop, daemon=True, name="anvi-ingestion-loop").start()
    port = int(__import__("os").environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
