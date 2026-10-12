import hashlib, json, os, time
from pathlib import Path
import requests

BASE = os.environ["ANVIQO_BASE_URL"].rstrip("/")
USERNAME = os.environ["ANVIQO_USERNAME"]
PASSWORD = os.environ["ANVIQO_PASSWORD"]
TIMEOUT = int(os.environ.get("ANVIQO_TEST_TIMEOUT", "90"))
EXPECTED_ORG = "org_c7d8a33263594bd1ab7004d9a5ea76ad"
EXPECTED_PLANT = "plant_e40ff33a053e4936ad29b1eafd012ca9"
SOURCE_URL = "https://raw.githubusercontent.com/rohitaei/ANVIQO/v2-v3-unified-industrial-intelligence/database/pci/pci_instrument_database.json"

s = requests.Session()
login = s.post(BASE + "/login", data={"username": USERNAME, "password": PASSWORD}, timeout=TIMEOUT, allow_redirects=False)
if login.status_code not in (200, 302, 303):
    raise SystemExit(f"LOGIN_FAILED status={login.status_code}")
ctx_resp = s.get(BASE + "/api/session/context", timeout=TIMEOUT)
ctx = ctx_resp.json()
if ctx_resp.status_code != 200 or ctx.get("organization_id") != EXPECTED_ORG or ctx.get("plant_id") != EXPECTED_PLANT:
    raise SystemExit("SAFETY_STOP: authenticated context is not the approved Primary Plant/org; no import attempted")

status_url = f"{BASE}/api/admin/onboarding/plant/{EXPECTED_PLANT}"
plant_resp = s.get(status_url, timeout=TIMEOUT)
if plant_resp.status_code != 200:
    raise SystemExit(f"ONBOARDING_STATUS_FAILED http={plant_resp.status_code}")
plant_status = plant_resp.json()
plant = plant_status.get("plant") or {}
if plant.get("slug") != "primary-plant" or plant.get("name") != "Primary Plant":
    raise SystemExit("SAFETY_STOP: target plant identity did not match Primary Plant")
docs = plant_status.get("documents") or []
summary_resp = s.get(status_url + "/knowledge-summary", timeout=TIMEOUT)
if summary_resp.status_code != 200:
    raise SystemExit(f"KNOWLEDGE_SUMMARY_FAILED http={summary_resp.status_code}")
summary = summary_resp.json()
if docs or int(summary.get("total_records") or 0) != 0:
    raise SystemExit("SAFETY_STOP: target plant already has documents/knowledge; refusing to overwrite or merge")

source_resp = requests.get(SOURCE_URL, timeout=TIMEOUT)
source_resp.raise_for_status()
source = source_resp.json()
records = source.get("records") or []
if len(records) != 1064 or source.get("source_document") != "PCI UPDATED DRAWING.xlsx":
    raise SystemExit(f"SAFETY_STOP: source contract mismatch records={len(records)} source={source.get('source_document')}")
pt = [r for r in records if str(r.get("tag") or "").strip().upper().replace("-", "_") == "PT_303"]
if len(pt) != 1 or pt[0].get("plc_address") != "PIW 260" or pt[0].get("tb_name") != "XC303":
    raise SystemExit("SAFETY_STOP: PT_303 source identity check failed")

# Give every source row a stable, unique external_id so duplicate tag labels
# across sheets are preserved rather than overwritten by the importer's upsert.
transformed = []
for i, raw in enumerate(records, 1):
    row = dict(raw)
    tag = str(row.get("tag") or "NO_TAG").strip().upper().replace("-", "_").replace(" ", "_")
    row["external_id"] = f"PCIJSON:{i:04d}:{tag}"
    row["record_type"] = "INSTRUMENT"
    row["source_document"] = source.get("source_document")
    transformed.append(row)
upload_doc = dict(source)
upload_doc["records"] = transformed
upload_bytes = json.dumps(upload_doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
digest = hashlib.sha256(upload_bytes).hexdigest()

upload = s.post(
    status_url + "/documents",
    files={"files": ("pci_instrument_database.json", upload_bytes, "application/json")},
    timeout=TIMEOUT,
)
if upload.status_code not in (200, 201):
    raise SystemExit(f"UPLOAD_FAILED http={upload.status_code} body={upload.text[:1000]}")
uploaded = upload.json()
if uploaded.get("status") != "OK":
    raise SystemExit(f"UPLOAD_FAILED response={json.dumps(uploaded)[:1000]}")

start = s.post(status_url + "/import", timeout=TIMEOUT)
if start.status_code != 200:
    raise SystemExit(f"IMPORT_START_FAILED http={start.status_code} body={start.text[:1000]}")
started = start.json()
if started.get("status") not in ("OK", "QUEUED"):
    raise SystemExit(f"IMPORT_START_FAILED response={json.dumps(started)[:1000]}")

deadline = time.time() + 240
final = {}
while time.time() < deadline:
    poll = s.get(status_url + "/import-status", timeout=TIMEOUT)
    if poll.status_code != 200:
        raise SystemExit(f"IMPORT_POLL_FAILED http={poll.status_code}")
    final = poll.json()
    state = str(final.get("job_status") or final.get("status") or "").upper()
    if state in ("SUCCEEDED", "FAILED", "ERROR", "BLOCKED"):
        break
    time.sleep(3)
else:
    raise SystemExit("IMPORT_TIMEOUT: worker did not finish within 240 seconds")

result = final.get("result") or {}
if str(final.get("job_status") or final.get("status") or "").upper() != "SUCCEEDED":
    raise SystemExit("IMPORT_FAILED: " + json.dumps(final, ensure_ascii=False)[:2500])
if int(result.get("records_available_to_anvi") or 0) != 1064 or int(result.get("error_count") or 0) != 0:
    raise SystemExit("IMPORT_INCOMPLETE: " + json.dumps(result, ensure_ascii=False)[:2500])

summary_after = s.get(status_url + "/knowledge-summary", timeout=TIMEOUT).json()
if int(summary_after.get("total_records") or 0) != 1064:
    raise SystemExit("KNOWLEDGE_COUNT_MISMATCH: " + json.dumps(summary_after, ensure_ascii=False)[:1000])

report = {
    "status": "PASS",
    "target_plant": {"plant_id": EXPECTED_PLANT, "organization_id": EXPECTED_ORG, "slug": plant.get("slug")},
    "source_document": source.get("source_document"),
    "source_sha256": hashlib.sha256(source_resp.content).hexdigest(),
    "uploaded_payload_sha256": digest,
    "source_records": len(records),
    "source_unique_tags_raw": len({str(r.get("tag") or "").strip() for r in records if str(r.get("tag") or "").strip()}),
    "imported_records": result.get("records_available_to_anvi"),
    "import_errors": result.get("error_count"),
    "knowledge_summary": summary_after,
    "pt_303_source_check": {"tag": pt[0].get("tag"), "description": pt[0].get("description"), "area": pt[0].get("area"), "plc_address": pt[0].get("plc_address"), "panel": pt[0].get("panel"), "tb_name": pt[0].get("tb_name"), "tb_no": pt[0].get("tb_no"), "io_type": pt[0].get("io_type"), "criticality": pt[0].get("criticality"), "source_sheet": pt[0].get("source_sheet")},
    "safety": {"plc_write": False, "scada_control": False, "automatic_execution": False, "human_decision_required": True},
}
Path("reports").mkdir(exist_ok=True)
Path("reports/ANVIQO_PRIMARY_PLANT_PCI_IMPORT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("PCI_IMPORT_PASS", "source_records=1064", "imported_records=1064", "errors=0", "plant=Primary Plant")
