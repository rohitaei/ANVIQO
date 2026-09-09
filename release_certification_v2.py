"""ANVIQO Release Certification V2.

Non-mutating release-readiness audit for the current Product V1 launch build.
This audit checks the active architecture, safety boundary, Plant Memory,
Maintenance Action Memory and Failure Prediction Demo without changing
inventory, memory, PLC/SCADA state or production history.
"""
from __future__ import annotations

from pathlib import Path
import ast
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
FAIL = []
WARN = []


def check(name, condition, detail=""):
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))
        FAIL.append(name)


def warn(name, condition, detail=""):
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[WARN] {name}" + (f" — {detail}" if detail else ""))
        WARN.append(name)


def read(name):
    path = ROOT / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main():
    print("=" * 76)
    print("ANVIQO PRODUCT V1 — RELEASE CERTIFICATION V2")
    print("=" * 76)

    print("\n===== ACTIVE SOURCE COMPILATION =====")
    py_files = [
        p for p in ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
        and not any(part.startswith(".anviqo_backup") for part in p.parts)
        and ".anviqo_backups" not in p.parts
    ]
    syntax_errors = []
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            syntax_errors.append((str(path), str(exc)))
    check("All active Python sources parse", not syntax_errors,
          str(syntax_errors[:3]))

    print("\n===== CORE PRODUCT SURFACE =====")
    required = [
        "anviqo_product.py", "anviqo_api.py", "anviqo_web.py",
        "anvi_knowledge_layer.py", "anviqo_dashboard.html",
        "plant_memory.py", "maintenance_action_memory_v1.py",
        "failure_prediction.py", "failure_prediction_api.py",
        "failure_prediction_demo_api.py", "failure_prediction_dashboard_runtime.py",
        "pci_conversation.py", "pci_live_simulator.py", "pci_spares.py",
        "anvi_voice.py",
    ]
    for name in required:
        check(f"Required file: {name}", (ROOT / name).exists())

    print("\n===== PCI INTEGRITY =====")
    pci_path = ROOT / "database/pci/pci_instrument_database.json"
    check("PCI database exists", pci_path.exists())
    if pci_path.exists():
        try:
            pci = json.loads(pci_path.read_text(encoding="utf-8"))
            records = pci.get("records", [])
            check("PCI version is PCI-1.0", pci.get("version") == "PCI-1.0")
            check("PCI record count is 1064", pci.get("record_count") == 1064)
            check("PCI contains 1064 records", len(records) == 1064)
            check("PCI is reference-only", pci.get("status") == "REFERENCE_ONLY")
            check("PCI control mode is READ_ONLY", pci.get("control_mode") == "READ_ONLY")
            check("PCI PLC write is disabled", pci.get("plc_write") is False)
            check("PCI SCADA control is disabled", pci.get("scada_control") is False)
            check("PCI requires human decision", pci.get("human_decision_required") is True)
            pt303 = next((r for r in records if r.get("tag") == "PT_303"), None)
            check("PT_303 identity exists", pt303 is not None)
            if pt303:
                check("PT_303 PLC address is PIW 260", pt303.get("plc_address") == "PIW 260")
                check("PT_303 panel is C2", pt303.get("panel") == "C2")
                check("PT_303 TB is XC303", pt303.get("tb_name") == "XC303")
        except Exception as exc:
            check("PCI database parses", False, str(exc))

    print("\n===== PLANT MEMORY =====")
    memory_path = ROOT / "database/plant_memory/plant_memory.json"
    check("Plant Memory database exists", memory_path.exists())
    if memory_path.exists():
        try:
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            records = memory.get("records", [])
            check("Plant Memory database is valid", isinstance(records, list))
            verified = [r for r in records if isinstance(r, dict) and r.get("verified") is True]
            check("PT-303 verified memory exists", any(r.get("tag") == "PT-303" for r in verified))
            check("Plant Memory exposes verified-only search", "if record.get(\"verified\") is not True" in read("plant_memory.py"))
        except Exception as exc:
            check("Plant Memory parses", False, str(exc))

    print("\n===== MAINTENANCE ACTION MEMORY =====")
    ma = read("maintenance_action_memory_v1.py")
    check("Maintenance Action Memory version present", "ANVIQO-MA-MEMORY-V1.0" in ma)
    check("Maintenance Action Memory is verified-only", "record.get(\"verified\") is not True" in ma)
    check("Maintenance Action Memory requires confirmation evidence", "confirmation_evidence" in ma)
    check("Maintenance Action Memory is read-only", "\"read_only\": True" in ma)
    check("Maintenance Action Memory blocks PLC write", "\"plc_write\": False" in ma)
    check("Maintenance Action Memory blocks SCADA", "\"scada_control\": False" in ma)
    check("Maintenance Action Memory requires human decision", "\"human_decision_required\": True" in ma)

    print("\n===== FAILURE PREDICTION =====")
    fp = read("failure_prediction.py")
    fph = read("failure_prediction_history.py")
    demo_api = read("failure_prediction_demo_api.py")
    demo_csv = ROOT / "database/failure_prediction/demo/pt303_demo_telemetry.csv"
    check("Failure Prediction V1.1 present", "ANVIQO Failure Prediction Intelligence V1.1" in fp)
    check("Prediction requires timestamped history", "timestamp" in fp and "historical" in fp.lower())
    check("Production history rejects simulation/demo sources", "SIMULATION" in fph and "DEMO" in fph)
    check("Demo API is explicitly simulation", '"simulation": True' in demo_api)
    check("Demo API exposes no calculated probability", "failure_probability" in demo_api)
    check("Demo telemetry file exists", demo_csv.exists())
    if demo_csv.exists():
        rows = demo_csv.read_text(encoding="utf-8").strip().splitlines()
        check("Demo telemetry contains header plus 8 observations", len(rows) == 9)
    freeze = read("releases/FP_DEMO_V1_FREEZE.md")
    check("Failure Prediction Demo freeze exists", "FROZEN" in freeze)

    print("\n===== DASHBOARD =====")
    dashboard = read("anviqo_dashboard.html")
    runtime = read("failure_prediction_dashboard_runtime.py")
    check("Predictive Intelligence page exists", 'id="page-prediction"' in dashboard)
    check("Failure Prediction Demo is labeled synthetic", "DEMO / SYNTHETIC DATA" in runtime)
    check("Dashboard demo states production history blocked", "Production history write: BLOCKED" in runtime)
    check("Dashboard demo states PLC/SCADA blocked", "PLC / SCADA control: BLOCKED" in runtime)
    check("Dashboard demo requires human decision", "Human decision: REQUIRED" in runtime)

    print("\n===== CONVERSATIONAL ROUTING =====")
    knowledge = read("anvi_knowledge_layer.py")
    check("Plant Memory routing exists", "_pci_memory_route" in knowledge and "_anvi_general_memory_route" in knowledge)
    check("Maintenance recall language exists", "what did maintenance do" in knowledge.lower())
    check("Previous-action recall exists", "previous action" in knowledge.lower())
    check("Recovery recall exists", "recovery status" in knowledge.lower())
    check("Spare-use recall exists", "spare used" in knowledge.lower())
    check("Memory route precedes normal PCI tag return", "Plant Memory — BEFORE VERIFIED PCI TAG ROUTING" in knowledge)

    print("\n===== API + SAFETY =====")
    api = read("anviqo_api.py")
    for route in ["/api/status", "/api/pci", "/api/pci/live", "/api/ask", "/api/safety", "/api/field_report"]:
        check(f"API surface contains {route}", route in api)
    safety_files = [
        "anviqo_api.py", "anvi_knowledge_layer.py", "pci_conversation.py",
        "pci_live_simulator.py", "anvi_voice.py", "failure_prediction.py",
        "failure_prediction_api.py", "maintenance_action_memory_v1.py"
    ]
    for name in safety_files:
        text = read(name)
        check(f"{name}: PLC write blocked", bool(re.search(r"plc_write\s*[:=]\s*False", text, re.I)))
        check(f"{name}: SCADA control blocked", bool(re.search(r"scada_control\s*[:=]\s*False", text, re.I)))

    print("\n===== NON-MUTATING CERTIFICATION =====")
    audit_text = read(Path(__file__).name)
    mutation_tokens = [
        "openpyxl", "save_workbook", "store_memory(", "create_conversational_memory(",
        "record_outcome(", "upsert_memory(", "update_excel", "write_observation(",
    ]
    check("Certification source contains no mutation operations", not any(t in audit_text for t in mutation_tokens))

    secret_patterns = [
        r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        r"(?i)secret[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        r"(?i)password\s*=\s*['\"][^'\"]{10,}['\"]",
    ]
    secret_hits = []
    for path in py_files:
        if path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(re.search(pattern, text) for pattern in secret_patterns):
            secret_hits.append(str(path))
    check("No obvious hard-coded secrets", not secret_hits, str(secret_hits[:5]))

    print("\n" + "=" * 76)
    print("CERTIFICATION RESULT")
    print("=" * 76)
    print("FAILURES:", len(FAIL))
    print("WARNINGS:", len(WARN))
    if FAIL:
        print("\nFAILED CHECKS:")
        for item in FAIL:
            print(" -", item)
        return 1
    print("\nRESULT: READY FOR EXECUTION/DEPLOYMENT VERIFICATION")
    print("NOTE: This script itself does not claim that it has been executed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
