"""ANVIQO Phase 6 Enterprise V4/V5 production entrypoint.

Loads the certified enterprise runtime, V4 context switching, and V5
context propagation adapters. Frozen V5 intelligence remains untouched.
"""
from phase6_enterprise_runtime import app
import phase6_enterprise_command_centre_v4  # noqa: F401,E402
import phase6_enterprise_context_v5  # noqa: F401,E402
import field_report_persistent_bridge  # noqa: F401,E402

__all__ = ["app"]
