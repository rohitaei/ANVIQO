"""ANVIQO plant-side edge runner.

Production entrypoint. Set ANVI_EDGE_MODE=SIMULATION for safe commissioning
without a PLC, or S7_READ_ONLY only after OT-approved configuration exists.
"""

from anvi_edge_runtime import main

if __name__ == "__main__":
    main()
