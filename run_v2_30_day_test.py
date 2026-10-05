"""ANVIQO V2 one-command 30-day end-to-end simulation runner.

Run from the repository root:
    python run_v2_30_day_test.py

This is a deterministic synthetic soak test. It does not certify live OT.
"""
from pathlib import Path
import json
from anvi_v2_month_soak_simulator import run_month_soak

def main():
    result = run_month_soak()
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / "ANVIQO_V2_30_DAY_SOAK_REPORT.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("\nANVIQO V2 — 30 DAY END-TO-END SOAK")
    print("=" * 42)
    stats = result.get("stats", {})
    for label, key in [
        ("Days simulated", "days"),
        ("Telemetry attempted", "telemetry_attempted"),
        ("Telemetry stored", "telemetry_stored"),
        ("Duplicate/reconnect", "duplicate_attempts"),
        ("Events", "events"),
        ("Replay windows", "replay_windows"),
        ("Tenant isolation blocks", "tenant_blocks"),
        ("PLC write blocks", "write_blocks"),
        ("Audit records", "audit_records"),
        ("Reports", "reports"),
    ]:
        print(f"{label:<27}: {stats.get(key)}")

    checks = [
        ("Software soak", result.get("status") == "PASS"),
        ("PoV gates", result.get("pov", {}).get("pov_ready") is True),
        ("PLC write", result.get("stored_snapshot", {}).get("plc_write") is False),
        ("SCADA control", result.get("stored_snapshot", {}).get("scada_control") is False),
    ]
    for label, ok in checks:
        print(f"{label:<27}: {'PASS' if ok else 'FAIL'}")

    print(f"\nReport: {report_path}")
    print("Real plant certification    : PENDING EXTERNAL EVIDENCE")
    print("Production deployment       : BLOCKED UNTIL APPROVAL")
    raise SystemExit(0 if all(ok for _, ok in checks) else 1)

if __name__ == "__main__":
    main()
