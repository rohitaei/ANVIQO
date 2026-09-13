"""Legacy ingestion worker retained only for compatibility."""
from __future__ import annotations
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify({"status": "DISABLED", "service": "anviqo-universal-ingestion-worker", "dispatcher": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
