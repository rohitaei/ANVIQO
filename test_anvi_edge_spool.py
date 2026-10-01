from pathlib import Path
from anvi_edge_spool import EdgeSpool

def test_bounded_spool_round_trip(tmp_path):
    spool = EdgeSpool(str(Path(tmp_path) / "spool.db"), max_batches=2, max_bytes=10000)
    item = spool.enqueue({"plant_id": "P1", "observations": [{"tag": "PT-303", "value": 43.2}]})
    assert item["queued"] is True
    assert len(spool.peek()) == 1
    assert spool.acknowledge(item["id"]) is True
    assert spool.status()["queued_batches"] == 0
