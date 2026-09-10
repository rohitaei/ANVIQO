"""ANVIQO Phase 6 Enterprise V4 production entrypoint.

Loads the certified enterprise runtime and the V4 context-switching adapter.
The underlying V5 intelligence remains untouched.
"""
from phase6_enterprise_runtime import app
import phase6_enterprise_command_centre_v4  # noqa: F401,E402

__all__ = ["app"]
