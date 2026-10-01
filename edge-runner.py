"""Minimal plant-side ANVIQO edge runner entrypoint.

Use only on the plant gateway/edge host. Configure the adapter separately;
this runner never writes to PLC/SCADA.
"""

from __future__ import annotations

import json
import os
import time

from anvi_edge_agent import EdgeAgent, EdgeAgentConfig
from anvi_edge_spool import EdgeSpool


def main():
    config = EdgeAgentConfig.from_env()
    spool = EdgeSpool()
    agent = EdgeAgent(config)
    print(json.dumps({"agent": agent.status(), "spool": spool.status()}, indent=2))
    interval = max(0.2, float(os.getenv("ANVI_EDGE_LOOP_SECONDS", "2")))

    # The live S7 adapter remains explicitly disabled until plant OT approval.
    # This runner is therefore a safe deployment scaffold, not an automatic
    # PLC connector.
    while True:
        time.sleep(interval)


if __name__ == "__main__":
    main()
