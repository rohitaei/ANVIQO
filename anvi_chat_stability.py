"""Compatibility entry point for the V1.4 universal tenant chat engine.

V1.5 adds a thin intelligence-experience envelope around the existing engine:
intent classification, evidence/context packaging and human-decision guidance.
The underlying V5/PCI engines remain unchanged and read-only.
"""
from anvi_chat_stability_v2 import (
    install as _base_install,
    _query_rows,
    _exact_answer,
    _summary_answer,
)


def install():
    _base_install()
    # sitecustomize can execute before anvi_chat_stability_v2 is imported.
    # Re-apply the membership context resolver after v2 is definitely loaded.
    try:
        import anvi_tenant_context_autofix as _context_fix
        import anvi_chat_stability_v2 as _stability
        _stability._plant_context = _context_fix.resolve_pair
        _stability._anviqo_membership_context_patch = True
    except Exception as exc:
        print(f"ANVIQO_CHAT_CONTEXT_REAPPLY_ERROR error={exc!r}", flush=True)

    try:
        import anvi_knowledge_layer as knowledge
        from anvi_intelligence_orchestrator import investigate
    except Exception:
        return
    current = getattr(knowledge, "ask_anvi", None)
    if not callable(current) or getattr(current, "_anviqo_intelligence_orchestrated", False):
        return

    def wrapped(question, *args, **kwargs):
        text = str(question or "").strip()
        try:
            result = investigate(
                text,
                _plant_id(),
                _plant_name(),
                lambda q: current(q, *args, **kwargs),
            )
            return result
        except Exception:
            return current(text, *args, **kwargs)

    wrapped._anviqo_intelligence_orchestrated = True
    knowledge.ask_anvi = wrapped


def _plant_id():
    try:
        from flask import session
        return session.get("plant_id")
    except Exception:
        return None


def _plant_name():
    try:
        from flask import session
        return session.get("plant_name") or session.get("plant") or "Selected plant"
    except Exception:
        return "Selected plant"


__all__ = ["install", "_query_rows", "_exact_answer", "_summary_answer"]
