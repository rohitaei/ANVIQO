from pathlib import Path
import ast, json, re, subprocess, sys

ROOT = Path(".")
FAIL = []
WARN = []

def ok(name, cond):
    print(f"[PASS] {name}" if cond else f"[FAIL] {name}")
    if not cond:
        FAIL.append(name)

def warn(name, cond):
    print(f"[PASS] {name}" if cond else f"[WARN] {name}")
    if not cond:
        WARN.append(name)

print("=" * 72)
print("ANVIQO V1.0 FINAL RELEASE AUDIT")
print("=" * 72)

# ============================================================
# 1. ACTIVE PYTHON SOURCE COMPILATION
# ============================================================
print("\n===== PYTHON COMPILATION =====")

py_files = []
for p in ROOT.rglob("*.py"):
    parts = set(p.parts)
    if any(x.startswith(".anviqo_backup") for x in parts):
        continue
    if "__pycache__" in parts:
        continue
    py_files.append(p)

compile_fail = []

for p in sorted(py_files):
    try:
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
    except Exception as e:
        compile_fail.append((str(p), str(e)))

ok("All active Python sources compile", not compile_fail)

if compile_fail:
    for f, e in compile_fail[:10]:
        print("  ", f, "->", e)

# ============================================================
# 2. CORE FILES
# ============================================================
print("\n===== CORE FILES =====")

required = [
    "anviqo_product.py",
    "anviqo_api.py",
    "anviqo_web.py",
    "anvi_knowledge_layer.py",
    "anvi_field_report.py",
    "pci_spares.py",
    "plant_memory.py",
    "pci_conversation.py",
    "pci_live_simulator.py",
    "anvi_voice.py",
    "anviqo_dashboard.html",
]

for name in required:
    ok(name, Path(name).exists())

# ============================================================
# 3. PCI DATABASE INTEGRITY
# ============================================================
print("\n===== PCI DATABASE =====")

pci_path = Path("database/pci/pci_instrument_database.json")
ok("PCI database exists", pci_path.exists())

if pci_path.exists():
    try:
        pci = json.loads(pci_path.read_text(encoding="utf-8"))

        ok("PCI version = PCI-1.0", pci.get("version") == "PCI-1.0")
        ok("PCI status = REFERENCE_ONLY",
           pci.get("status") == "REFERENCE_ONLY")
        ok("PCI control mode = READ_ONLY",
           pci.get("control_mode") == "READ_ONLY")
        ok("PCI PLC write disabled",
           pci.get("plc_write") is False)
        ok("PCI SCADA control disabled",
           pci.get("scada_control") is False)
        ok("Human decision required",
           pci.get("human_decision_required") is True)
        ok("PCI record count = 1064",
           pci.get("record_count") == 1064)

        records = pci.get("records", [])
        ok("PCI contains 1064 records", len(records) == 1064)

        tags = [str(r.get("tag","")) for r in records]
        ok("PCI tags are unique", len(tags) == len(set(tags)))

        pt303 = next((r for r in records if r.get("tag") == "PT_303"), None)
        ok("PT_303 exists", pt303 is not None)

        if pt303:
            ok("PT_303 PLC address = PIW 260",
               pt303.get("plc_address") == "PIW 260")
            ok("PT_303 panel = C2",
               pt303.get("panel") == "C2")
            ok("PT_303 TB = XC303",
               pt303.get("tb_name") == "XC303")

    except Exception as e:
        print("[FAIL] PCI database parse:", e)
        FAIL.append("PCI database parse")

# ============================================================
# 4. CRITICAL SPARES
# ============================================================
print("\n===== CRITICAL SPARES =====")

try:
    import pci_spares

    db = Path("database/spares/critical_spares.xlsx")
    ok("Critical spares workbook exists", db.exists())

    ok("Spare module imports", True)

    tests = [
        ("flow transmitter", "FT"),
        ("pressure transmitter", "PT"),
        ("level transmitter", "LT"),
        ("RTD", "RTD"),
        ("motorized control valve", "MCV"),
        ("SOV", "SOV"),
        ("positioner", "POS'R"),
        ("load cell", "LOAD CELL"),
        ("analyser", "Analyser"),
    ]

    for q, expected in tests:
        result = pci_spares.answer_spare_management_v16(q)
        text = str(result)
        ok(f"Spare category: {q} -> {expected}",
           expected in text)

    result = pci_spares.answer_spare_management_v16("Do we have a spare for PT-303?")
    ok("PT-303 spare query works", "PT-303" in str(result))

except Exception as e:
    print("[FAIL] Critical spares audit:", e)
    FAIL.append("Critical spares audit")

# ============================================================
# 5. SPARE MUTATION SAFETY — NO ACTUAL MUTATION
# ============================================================
print("\n===== SPARE MUTATION SAFETY =====")

try:
    import pci_spares

    for q in [
        "add 3 PT-303",
        "I used 1 PT-303 spare",
        "use 999999 PT-303",
    ]:
        result = pci_spares.answer_spare_management_v16(q, confirmed=False)
        ok(f"Unconfirmed mutation blocked: {q}",
           "confirmation" in str(result).lower()
           or "confirm" in str(result).lower()
           or "not executed" in str(result).lower()
           or "pending" in str(result).lower())

except Exception as e:
    print("[FAIL] Spare mutation safety:", e)
    FAIL.append("Spare mutation safety")

# ============================================================
# 6. PLANT MEMORY
# ============================================================
print("\n===== PLANT MEMORY =====")

try:
    import plant_memory

    memory_file = Path("database/plant_memory/plant_memory.json")
    ok("Plant Memory database exists", memory_file.exists())

    memories = plant_memory.search_all_memory("")
    ok("Plant Memory readable", isinstance(memories, list))
    ok("PT-303 memory exists",
       any("PT-303" in str(x.get("tag","")) for x in memories))

    for name in [
        "create_memory",
        "create_conversational_memory",
        "verify_memory",
        "search_all_memory",
    ]:
        ok(f"Plant Memory API: {name}",
           hasattr(plant_memory, name))

except Exception as e:
    print("[FAIL] Plant Memory audit:", e)
    FAIL.append("Plant Memory audit")

# ============================================================
# 7. FIELD REPORT
# ============================================================
print("\n===== FIELD REPORT =====")

try:
    from anvi_field_report import parse_field_report

    ups = """During my visit to the main center plant, I noticed that the
inverter light on UPS 2 was off and the hooter was sounding continuously.
I then reset the UPS and power-cycled it (turned it off and back on).
After that, I saw that the inverter light turned on and everything went
back to normal. However, a short while later, I noticed that the SPP light
had turned on and the inverter's hooter started making a sound again.
I reset it once more. I saw that everything returned to normal, but the
SPP light is now blinking intermittently. with a present sandip mondal"""

    r = parse_field_report(ups)

    ok("UPS-2 detected", r.get("equipment") == "UPS-2")
    ok("UPS-2 location detected",
       r.get("area","").strip().lower() == "main center plant")
    ok("Present-with detected",
       "sandip mondal" in r.get("present_with","").lower())
    ok("UPS root cause not invented",
       not r.get("root_cause"))
    ok("UPS current condition retained",
       "blinking intermittently" in (
           str(r.get("outcome","")) + " " +
           str(r.get("confirmation_evidence",""))
       ).lower())

    pt = parse_field_report(
        "pt-303 was not showing any thing checked fuse blown no power "
        "changed fuse now ok"
    )

    ok("PT-303 detected", pt.get("equipment") == "PT-303")
    ok("PT-303 fuse finding detected",
       "fuse blown" in pt.get("finding","").lower())
    ok("PT-303 fuse action detected",
       "fuse" in pt.get("maintenance_action","").lower())
    ok("PT-303 recovery detected",
       pt.get("recovery_status") == "Recovered")

except Exception as e:
    print("[FAIL] Field report audit:", e)
    FAIL.append("Field report audit")

# ============================================================
# 8. NATURAL TROUBLESHOOTING
# ============================================================
print("\n===== NATURAL TROUBLESHOOTING =====")

try:
    from anvi_knowledge_layer import (
        _anvi_troubleshooting_question,
        _anviqo_authoritative_core
    )

    positive = [
        "PT-303 is fluctuating",
        "PT-303 is unstable",
        "PT-303 is giving wrong pressure",
        "PT-303 suddenly went high",
        "PT-303 is showing zero",
        "PT-303 signal is intermittent",
        "PT-303 is not responding",
        "What should I check in PT-303?",
        "Why is PT-303 fluctuating?",
        "What could be wrong with PT-303?",
        "What happened to PT-303 last time?",
        "What did maintenance find on PT-303?",
    ]

    negative = [
        "What is PT-303?",
        "Tell me about PT-303",
        "What is the PLC address of PT-303?",
    ]

    for q in positive:
        ok("TR | " + q, _anvi_troubleshooting_question(q))

    for q in negative:
        ok("NON-TR | " + q, not _anvi_troubleshooting_question(q))

    routes = {
        "PT-303 is fluctuating": "troubleshooting",
        "PT-303 is giving wrong pressure": "troubleshooting",
        "What happened to PT-303 last time?": "plant_memory",
        "What did maintenance find on PT-303?": "plant_memory",
    }

    for q, expected in routes.items():
        ans = _anviqo_authoritative_core(q)
        ok("Routing | " + q,
           isinstance(ans, dict) and ans.get("domain") == expected)

except Exception as e:
    print("[FAIL] Troubleshooting audit:", e)
    FAIL.append("Troubleshooting audit")

# ============================================================
# 9. API ROUTES
# ============================================================
print("\n===== API ROUTES =====")

api_text = Path("anviqo_api.py").read_text(encoding="utf-8")

routes = [
    "/login",
    "/logout",
    "/api/status",
    "/api/pci",
    "/api/pci/live",
    "/api/ask",
    "/api/safety",
    "/api/equipment/<tag>",
    "/api/equipment/<tag>/relationships",
    "/api/equipment/<tag>/events",
    "/api/plant/<area>",
    "/api/maintenance",
    "/api/management",
    "/api/plant_snapshot",
    "/api/field_report",
]

for route in routes:
    ok("API route present: " + route, route in api_text)

# ============================================================
# 10. SAFETY CONTRACT
# ============================================================
print("\n===== SAFETY CONTRACT =====")

safety_files = [
    "anviqo_api.py",
    "anvi_knowledge_layer.py",
    "anvi_field_report.py",
    "pci_spares.py",
    "pci_conversation.py",
    "pci_live_simulator.py",
    "anvi_voice.py",
]

for filename in safety_files:
    text = Path(filename).read_text(encoding="utf-8")

    ok(filename + " PLC write disabled",
       re.search(r"plc_write\s*[:=]\s*False", text) is not None)

    ok(filename + " SCADA control disabled",
       re.search(r"scada_control\s*[:=]\s*False", text) is not None)

# ============================================================
# 11. SECRET / CREDENTIAL CHECK
# ============================================================
print("\n===== SECRET CHECK =====")

secret_patterns = [
    r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{12,}['\"]",
    r"(?i)secret[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{12,}['\"]",
    r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]",
]

secret_hits = []

for p in py_files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except:
        continue

    for pattern in secret_patterns:
        if re.search(pattern, text):
            secret_hits.append(str(p))

ok("No obvious hard-coded secrets", not secret_hits)

if secret_hits:
    for x in sorted(set(secret_hits)):
        print("  ", x)

# ============================================================
# 12. DUPLICATE / ACCIDENTAL ARTIFACT CHECK
# ============================================================
print("\n===== ARTIFACT CHECK =====")

backup_dirs = list(ROOT.glob(".anviqo_backup_*")) + [ROOT / ".anviqo_backups"]

warn(
    "No runtime backup directories inside release tree",
    not any(p.exists() for p in backup_dirs)
)

tracked_status = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True,
    text=True
).stdout

print("\n===== GIT STATUS =====")
print(tracked_status if tracked_status.strip() else "[CLEAN]")

deletion_lines = [
    x for x in tracked_status.splitlines()
    if x.startswith("D ") or x.startswith(" D")
]

ok(
    "No accidental tracked-file deletions",
    not deletion_lines
)

# ============================================================
# 13. DUPLICATE INTELLIGENCE MODULE CHECK
# ============================================================
print("\n===== INTELLIGENCE ARCHITECTURE =====")

intelligence_names = [
    "plant_health",
    "plant_health_intelligence",
    "event_correlation",
    "cross_equipment_correlation",
    "relationship_aware_correlation",
    "maintenance_intelligence",
    "shift_intelligence",
    "plant_memory",
]

existing = []

for name in intelligence_names:
    matches = list(ROOT.glob(name + ".py"))
    if matches:
        existing.append(name)

print("Existing intelligence modules:", ", ".join(existing))

ok(
    "Core intelligence modules remain singular",
    all(len(list(ROOT.glob(name + ".py"))) <= 1 for name in intelligence_names)
)

# ============================================================
# FINAL
# ============================================================
print("\n" + "=" * 72)
print("FINAL RELEASE AUDIT")
print("=" * 72)

print("FAILURES :", len(FAIL))
print("WARNINGS :", len(WARN))

if FAIL:
    print("\nRELEASE AUDIT: FAIL")
    for x in FAIL:
        print(" -", x)
    sys.exit(1)

print("\nRELEASE AUDIT: PASS")

if WARN:
    print("\nWarnings requiring review:")
    for x in WARN:
        print(" -", x)
