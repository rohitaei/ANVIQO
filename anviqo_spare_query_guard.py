"""ANVIQO production entrypoint with safe V1.8 spare intent guard."""
from __future__ import annotations
import re


def _is_read_question(question: str) -> bool:
    q = str(question or "").strip().lower()
    if not q:
        return False
    if "?" in q:
        return True
    return q.startswith((
        "what ", "which ", "where ", "when ", "why ", "how ",
        "is ", "are ", "was ", "were ", "did ", "do ", "does ",
        "can ", "could ", "would ", "will ", "show ", "tell me ",
        "give me ", "find ", "list ",
    ))

import pci_spares

_original_v18_action = getattr(pci_spares, "_v18_action", None)
if callable(_original_v18_action):
    def _guarded_v18_action(question, _original=_original_v18_action):
        if _is_read_question(question):
            return None
        return _original(question)
    pci_spares._v18_action = _guarded_v18_action

# Preserve the existing Phase 2 production API and frozen V5 intelligence.
from anviqo_api_phase2 import app  # noqa: E402
