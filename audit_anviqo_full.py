from pathlib import Path
import json
import importlib
import sys

ROOT = Path(__file__).resolve().parent

PASS = 0
WARN = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, WARN, FAIL

    if condition:
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
        PASS += 1
    else:
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))
        FAIL += 1

def warn(name, detail=""):
    global WARN
    print(f"[WARN] {name}" + (f" — {detail}" if detail else ""))
    WARN += 1

def module_exists(name):
    try:
        importlib.import_module(name)
        return True
    except Exception as e:
        print(f"       Import error: {e}")
        return False

print("=" * 70)
print(" ANVIQO FULL SYSTEM AUDIT — READ ONLY")
print("=" * 70)
print("PROJECT:", ROOT)
print("Python:", sys.version.split()[0])
print()

# ------------------------------------------------------------
# 1. CORE FILES
# ------------------------------------------------------------

print("===== 1. CORE FILES =====")

core_files = [
    "anviqo_product.py",
    "anviqo_api.py",
    "anviqo_web.py",
    "pci_conversation.py",
    "pci_spares.py",
    "pci_spare_direct_excel.py",
    "pci_spare_transactions.py",
    "anvi_knowledge_layer.py",
]

for f in core_files:
    check(
        f,
        (ROOT / f).exists(),
        "exists" if (ROOT / f).exists() else "missing"
    )

print()

# ------------------------------------------------------------
# 2. DATABASES
# ------------------------------------------------------------

print("===== 2. DATABASE / EVIDENCE =====")

db_files = [
    "database/pci/pci_instrument_database.json",
    "database/spares/critical_spares.xlsx",
]

for f in db_files:
    p = ROOT / f
    check(f, p.exists(), "exists" if p.exists() else "missing")

pci = ROOT / "database/pci/pci_instrument_database.json"

if pci.exists():
    try:
        data = json.loads(pci.read_text(encoding="utf-8"))

        record_count = data.get("record_count")
        plc_write = data.get("plc_write")
        scada_control = data.get("scada_control")
        read_only = data.get("control_mode") == "READ_ONLY"

        print("PCI record_count:", record_count)
        print("PCI control_mode:", data.get("control_mode"))
        print("PCI plc_write:", plc_write)
        print("PCI scada_control:", scada_control)

        check(
            "PCI record count",
            isinstance(record_count, int) and record_count > 0,
            str(record_count)
        )

        check(
            "PCI READ_ONLY",
            read_only,
            str(data.get("control_mode"))
        )

        check(
            "PCI PLC write disabled",
            plc_write is False,
            str(plc_write)
        )

        check(
            "PCI SCADA control disabled",
            scada_control is False,
            str(scada_control)
        )

    except Exception as e:
        print("PCI JSON ERROR:", e)
        FAIL += 1

print()

# ------------------------------------------------------------
# 3. SPARE ENGINE
# ------------------------------------------------------------

print("===== 3. SPARE ENGINE =====")

check(
    "Direct Excel spare engine import",
    module_exists("pci_spare_direct_excel")
)

try:
    from pci_spare_direct_excel import get_spare_quantity

    qty = get_spare_quantity("PT-303")

    print("PT-303 CURRENT EXCEL QTY:", qty)

    check(
        "PT-303 readable from Excel",
        qty >= 0,
        str(qty)
    )

except Exception as e:
    print("PT-303 ERROR:", e)
    FAIL += 1

print()

# ------------------------------------------------------------
# 4. SPARE TRANSACTION HISTORY
# ------------------------------------------------------------

print("===== 4. SPARE AUDIT / HISTORY =====")

txn_file = ROOT / "database/spares/critical_spare_transactions.json"

if txn_file.exists():
    try:
        tx = json.loads(txn_file.read_text(encoding="utf-8"))
        transactions = tx.get("transactions", [])

        print("Direct/audit transactions:", len(transactions))

        if transactions:
            last = transactions[-1]
            print("Last action:", last.get("action"))
            print("Last tag:", last.get("tag"))
            print("Last quantity:", last.get("quantity"))
            print("Last status:", last.get("status"))

        check(
            "Spare audit file readable",
            True,
            f"{len(transactions)} records"
        )

    except Exception as e:
        print("Transaction JSON ERROR:", e)
        FAIL += 1
else:
    warn("Spare audit file", "not created yet")

print()

# ------------------------------------------------------------
# 5. CONVERSATIONAL ENGINE
# ------------------------------------------------------------

print("===== 5. CONVERSATIONAL INTELLIGENCE =====")

check(
    "PCI conversation import",
    module_exists("pci_conversation")
)

if module_exists("pci_conversation"):
    try:
        from pci_conversation import answer

        questions = [
            "ANVI, what is the current spare quantity of PT-303?",
            "ANVI, tell me about PT-303",
            "ANVI, show available MCV spares",
        ]

        for q in questions:
            print()
            print("QUERY:", q)

            try:
                r = answer(q)

                if isinstance(r, dict):
                    text = r.get("answer", "")
                else:
                    text = str(r)

                print("RESPONSE:")
                print(text[:1200])

                check(
                    "Conversation response",
                    bool(text.strip()),
                    "response received"
                )

            except Exception as e:
                print("QUERY ERROR:", e)
                FAIL += 1

    except Exception as e:
        print("Conversation engine ERROR:", e)
        FAIL += 1

print()

# ------------------------------------------------------------
# 6. KNOWLEDGE LAYER
# ------------------------------------------------------------

print("===== 6. KNOWLEDGE ROUTER =====")

check(
    "ANVI knowledge layer import",
    module_exists("anvi_knowledge_layer")
)

print()

# ------------------------------------------------------------
# 7. VOICE
# ------------------------------------------------------------

print("===== 7. VOICE =====")

voice_candidates = [
    "anvi_voice.py",
    "voice_interface.py",
]

voice_found = []

for f in voice_candidates:
    if (ROOT / f).exists():
        voice_found.append(f)

if voice_found:
    check(
        "Voice module",
        True,
        ", ".join(voice_found)
    )
else:
    warn(
        "Voice module",
        "named voice file not found at project root"
    )

# Search code for safety flags.
print()
print("Voice / safety references:")

for f in [
    "anvi_voice.py",
    "pci_conversation.py",
    "anvi_knowledge_layer.py",
    "anviqo_api.py",
]:
    p = ROOT / f
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="ignore").lower()

        hits = []

        for term in [
            "plc_write",
            "scada_control",
            "human_decision_required",
            "read_only",
            "speech_to_text",
            "text_to_speech",
        ]:
            if term in text:
                hits.append(term)

        if hits:
            print(f"{f}: {', '.join(hits)}")

print()

# ------------------------------------------------------------
# 8. API / WEB
# ------------------------------------------------------------

print("===== 8. API / WEB =====")

check(
    "API module",
    (ROOT / "anviqo_api.py").exists()
)

check(
    "Web module",
    (ROOT / "anviqo_web.py").exists()
)

# ------------------------------------------------------------
# 9. ROUTES / ENDPOINTS
# ------------------------------------------------------------

print()
print("===== 9. API ENDPOINT AUDIT =====")

api = ROOT / "anviqo_api.py"

if api.exists():
    text = api.read_text(encoding="utf-8", errors="ignore")

    for endpoint in [
        "/api/status",
        "/api/pci",
        "/api/ask",
    ]:
        check(
            endpoint,
            endpoint in text,
            "found in API source" if endpoint in text else "not found"
        )

print()

# ------------------------------------------------------------
# 10. SAFETY AUDIT
# ------------------------------------------------------------

print("===== 10. SAFETY BOUNDARY =====")

all_python = ""

for p in ROOT.glob("*.py"):
    try:
        all_python += "\n" + p.read_text(
            encoding="utf-8",
            errors="ignore"
        ).lower()
    except Exception:
        pass

check(
    "PLC write protection references",
    "plc_write" in all_python
)

check(
    "SCADA control protection references",
    "scada_control" in all_python
)

check(
    "Human decision boundary",
    "human_decision_required" in all_python
)

print()

# ------------------------------------------------------------
# 11. GIT STATUS — READ ONLY
# ------------------------------------------------------------

print("===== 11. GIT STATUS =====")

import subprocess

try:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    print(result.stdout)

    check(
        "Git repository",
        result.returncode == 0,
        "git status readable"
    )

except Exception as e:
    warn("Git status", str(e))

print()

# ------------------------------------------------------------
# 12. FILE COUNTS
# ------------------------------------------------------------

print("===== 12. PROJECT INVENTORY =====")

try:
    py_files = list(ROOT.rglob("*.py"))
    json_files = list(ROOT.rglob("*.json"))
    xlsx_files = list(ROOT.rglob("*.xlsx"))
    html_files = list(ROOT.rglob("*.html"))

    print("Python files :", len(py_files))
    print("JSON files   :", len(json_files))
    print("Excel files  :", len(xlsx_files))
    print("HTML files   :", len(html_files))

except Exception as e:
    print("Inventory error:", e)

print()

# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------

print("=" * 70)
print(" ANVIQO FULL AUDIT RESULT")
print("=" * 70)

print("PASS :", PASS)
print("WARN :", WARN)
print("FAIL :", FAIL)

print()

if FAIL == 0:
    print("OVERALL: PASS — No blocking failure detected.")
else:
    print("OVERALL: ACTION REQUIRED — Review FAIL items before next build.")

print()
print("IMPORTANT:")
print("This audit is READ ONLY.")
print("No Excel quantity was changed.")
print("No spare transaction was created.")
print("No Git files were modified.")
print("=" * 70)
