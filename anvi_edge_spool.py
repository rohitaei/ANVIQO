"""Bounded local spool for plant-side ANVIQO edge delivery.

The spool is intentionally local to the plant gateway. It stores only
normalized observation batches, has a hard item/byte bound, and can be
replayed after cloud connectivity returns. No PLC/SCADA writes are present.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List


class EdgeSpool:
    def __init__(self, path: str | None = None, max_batches: int = 1000, max_bytes: int = 50_000_000):
        self.path = Path(path or os.getenv("ANVI_EDGE_SPOOL", "./anvi_edge_spool.db"))
        self.max_batches = max(1, int(max_batches))
        self.max_bytes = max(1024, int(max_bytes))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload TEXT NOT NULL,
                size_bytes INTEGER NOT NULL
            )""")
            c.commit()

    def _stats(self, c):
        row = c.execute("SELECT COUNT(*) n, COALESCE(SUM(size_bytes),0) b FROM batches").fetchone()
        return int(row["n"]), int(row["b"])

    def enqueue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        size = len(raw.encode("utf-8"))
        if size > self.max_bytes:
            raise ValueError("edge batch exceeds maximum spool size")
        with self._connect() as c:
            count, total = self._stats(c)
            if count >= self.max_batches or total + size > self.max_bytes:
                raise OverflowError("edge spool capacity reached; cloud delivery required before accepting more")
            item_id = uuid.uuid4().hex
            c.execute("INSERT INTO batches(id,payload,size_bytes) VALUES(?,?,?)", (item_id, raw, size))
            c.commit()
        return {"id": item_id, "queued": True, "size_bytes": size}

    def peek(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as c:
            rows = c.execute("SELECT id,payload,size_bytes,created_at FROM batches ORDER BY created_at,id LIMIT ?", (max(1, int(limit)),)).fetchall()
        return [{"id": r["id"], "payload": json.loads(r["payload"]), "size_bytes": r["size_bytes"], "created_at": r["created_at"]} for r in rows]

    def acknowledge(self, item_id: str) -> bool:
        with self._connect() as c:
            cur = c.execute("DELETE FROM batches WHERE id=?", (item_id,))
            c.commit()
            return cur.rowcount == 1

    def status(self) -> Dict[str, Any]:
        with self._connect() as c:
            count, total = self._stats(c)
        return {"status": "READY", "queued_batches": count, "queued_bytes": total,
                "max_batches": self.max_batches, "max_bytes": self.max_bytes}


def self_test() -> Dict[str, Any]:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        spool = EdgeSpool(str(Path(d) / "spool.db"), max_batches=2, max_bytes=10000)
        first = spool.enqueue({"plant_id": "P1", "observations": [{"tag": "PT-303", "value": 43.2}]})
        assert first["queued"]
        assert len(spool.peek()) == 1
        assert spool.acknowledge(first["id"])
        assert spool.status()["queued_batches"] == 0
        return {"status": "PASS"}


if __name__ == "__main__":
    print(self_test())
