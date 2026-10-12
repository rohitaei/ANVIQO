import json, os, re
from pathlib import Path
import requests

BASE = os.environ["ANVIQO_BASE_URL"].rstrip("/")
USERNAME = os.environ["ANVIQO_USERNAME"]
PASSWORD = os.environ["ANVIQO_PASSWORD"]
TIMEOUT = int(os.environ.get("ANVIQO_TEST_TIMEOUT", "90"))
QUESTIONS = [
    "Tell me about PT-303.",
    "Show the PLC and I/O intelligence for PT-303.",
    "Which area contains PT-303?",
    "What could explain the PT-303 pressure change?",
    "What evidence supports the PT-303 diagnosis?",
    "Simulate a change on PT-303 and explain it.",
    "Trace the evidence for PT-303.",
    "Show the historical pattern for PT-303.",
    "Analyze PT-303 using all available evidence.",
    "have we seen this before on PT-303",
    "is PT-303 getting worse",
    "give me an early warning for PT-303",
    "did PT-303 recover",
    "what happens if PT-303 continues increasing",
    "show PT-303 instrument health",
    "how confident are you about PT-303",
]
s = requests.Session()
login = s.post(BASE + "/login", data={"username": USERNAME, "password": PASSWORD}, timeout=TIMEOUT, allow_redirects=False)
if login.status_code not in (200, 302, 303):
    raise SystemExit(f"LOGIN_FAILED status={login.status_code}")
context = s.get(BASE + "/api/session/context", timeout=TIMEOUT)
context_payload = {}
try: context_payload = context.json()
except Exception: pass
results = []
for i, question in enumerate(QUESTIONS, 1):
    try:
        response = s.post(BASE + "/api/ask", json={"question": question}, timeout=TIMEOUT)
        try: payload = response.json()
        except Exception: payload = {"_non_json_body": response.text[:3000]}
        answer = payload.get("answer") or payload.get("response") or "" if isinstance(payload, dict) else ""
        results.append({
            "number": i, "question": question, "http": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "answer": str(answer)[:12000],
            "raw_response": payload,
        })
    except Exception as exc:
        results.append({"number": i, "question": question, "http": None, "error": type(exc).__name__ + ": " + str(exc), "answer": "", "raw_response": None})
out = {
    "base_url": BASE,
    "login_status": login.status_code,
    "session_context_http": context.status_code,
    "session_context": context_payload,
    "total": len(QUESTIONS),
    "answered": sum(bool(str(x.get("answer") or "").strip()) for x in results),
    "blank_answers": [x["number"] for x in results if not str(x.get("answer") or "").strip()],
    "results": results,
}
Path("reports").mkdir(exist_ok=True)
Path("reports/ANVIQO_LIVE_FAILURE_DIAGNOSTIC.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("DIAGNOSTIC_TOTAL", out["total"], "ANSWERED", out["answered"], "BLANK", out["blank_answers"])
for item in results:
    if not str(item.get("answer") or "").strip():
        print("BLANK", item["number"], item["question"], "HTTP", item.get("http"), "KEYS", item.get("top_level_keys"), "RAW", json.dumps(item.get("raw_response"), ensure_ascii=False)[:1200])
if out["blank_answers"]:
    raise SystemExit(1)
