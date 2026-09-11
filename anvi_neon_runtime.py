"""
ANVIQO Neon runtime bootstrap.

Neon is persistent operational storage when DATABASE_URL exists.
Local JSON/Excel remains fallback when it does not.
No PLC or SCADA write is performed.
"""

def bootstrap():
    try:
        from anvi_neon_store import neon_enabled, init_neon
        if neon_enabled():
            return bool(init_neon())
    except Exception:
        return False
    return False

BOOTSTRAP_RESULT=bootstrap()

# Install the tenant-aware Command Centre data adapter after persistence
# bootstrap and before the API's legacy snapshot routes are exercised.
try:
    import anvi_universal_command_centre
except Exception:
    pass
