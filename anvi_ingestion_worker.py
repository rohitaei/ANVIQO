"""ANVIQO durable universal ingestion dispatcher."""
from __future__ import annotations
import json, os, threading, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from flask import Flask, jsonify

app = Flask(__name__)

def _dispatch_once():
    base = os.environ.get("ANVI_WEB_URL", "https://anviqo.onrender.com").rstrip("/")
    token = os.environ.get("ANVI_INGESTION_DISPATCH_TOKEN", "").strip()
    if not token:
        raise RuntimeError("ANVI_INGESTION_DISPATCH_TOKEN is required")
    req = Request(f"{base}/api/internal/ingestion/dispatch", method="POST", headers={"X-ANVI-INGESTION-TOKEN": token, "Content-Type": "application/json"}, data=b"{}")
    with urlopen(req, timeout=110) as response:
        return json.loads(response.read().decode("utf-8"))

def _worker_loop():
    while True:
        try:
            result = _dispatch_once()
            print(f"ANVI universal ingestion dispatcher: processed={result.get('processed', 0)} job={result.get('job_id', '-')}", flush=True)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"ANVI universal ingestion dispatcher HTTP error: {exc}", flush=True)
        except Exception as exc:
            print(f"ANVI universal ingestion dispatcher error: {exc}", flush=True)
        time.sleep(5)

@app.get("/health")
def health():
    return jsonify({"status": "OK", "service": "anviqo-universal-ingestion-worker"})

if __name__ == "__main__":
    threading.Thread(target=_worker_loop, daemon=True, name="anvi-ingestion-loop").start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
