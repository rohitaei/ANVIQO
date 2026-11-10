"""ANVIQO production entrypoint with safe spare intent and repair command guard."""
from __future__ import annotations
import re

def _is_read_question(question: str) -> bool:
    q = str(question or "").strip().lower()
    if not q:
        return False
    if "?" in q:
        return True
    return q.startswith(("what ", "which ", "where ", "when ", "why ", "how ", "is ", "are ", "was ", "were ", "did ", "do ", "does ", "can ", "could ", "would ", "will ", "show ", "tell me ", "give me ", "find ", "list "))


def _is_reconcile_command(question: str) -> bool:
    q = re.sub(r"[^a-z0-9-]+", " ", str(question or "").strip().lower())
    return "reconcile" in q and "spare" in q and ("field report" in q or "report" in q)


def _extract_tag(question: str) -> str:
    m = re.search(r"\b([a-z]{1,8}[- ]?\d{1,5})\b", str(question or ""), re.I)
    return m.group(1).upper().replace(" ", "-") if m else ""


import pci_spares

_original_v18_action = getattr(pci_spares, "_v18_action", None)
if callable(_original_v18_action):
    def _guarded_v18_action(question, _original=_original_v18_action):
        if _is_read_question(question) or _is_reconcile_command(question):
            return None
        return _original(question)
    pci_spares._v18_action = _guarded_v18_action

from anviqo_api_phase2 import app  # noqa: E402
import failure_prediction_api  # noqa: E402,F401

# IMPORTANT: inventory reconciliation is deliberately NOT attached to
# /api/ask or Flask before_request. The conversational endpoint may receive
# a transcript containing earlier user turns; interpreting transcript text
# as a fresh write command can decrement stock repeatedly and block the
# chat worker while loading the Excel workbook. Reconciliation must use a
# separate, tenant-scoped, explicitly confirmed write workflow. Until that
# workflow is provided, chat remains read-only and never mutates inventory.


# Plant login, tenant-scoped account provisioning and plant-user management
# are registered on this same production Flask app.
import anvi_plant_runtime_bridge  # noqa: E402,F401
