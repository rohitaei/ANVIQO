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


def _resolve_context():
    """Return the single authoritative authenticated plant context."""
    import anvi_tenant_context_autofix as _context_fix
    pid, oid, source = _context_fix.resolve()
    return pid, oid, source


def install():
    _base_install()
    # Re-apply the authoritative membership resolver after v2 is definitely
    # loaded. This is routing/context only; V5/PCI remain untouched.
    try:
        import anvi_tenant_context_autofix as _context_fix
        import anvi_chat_stability_v2 as _stability
        _stability._plant_context = _context_fix.resolve_pair
        _stability._anviqo_membership_context_patch = True

        # The answer wrapper is deliberately retained as a second guard. The
        # actual v2 answer function also resolves membership, so stale session
        # plant_id values cannot become a cross-plant lookup.
        if not getattr(_stability, "_anviqo_answer_membership_patch", False):
            _original_answer = _stability._answer

            def _membership_scoped_answer(text, *args, **kwargs):
                _context_fix.resolve()
                return _original_answer(text, *args, **kwargs)

            _stability._answer = _membership_scoped_answer
            _stability._anviqo_answer_membership_patch = True
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
            # Resolve membership at the request boundary, then pass the same
            # authoritative context into the intelligence envelope. The UI is
            # not a plant selector and stale session context is never trusted.
            pid, oid, source = _resolve_context()
            if not pid:
                if source == "MULTIPLE_AUTHORIZED_PLANTS":
                    return {
                        "answer": "Multiple authorized plants are available for this account. ANVI requires an explicit plant context and will not guess or use another plant.",
                        "blocked": True,
                        "reason": "MULTIPLE_AUTHORIZED_PLANTS",
                        "tenant_scoped": True,
                        "read_only": True,
                        "plc_write": False,
                        "scada_control": False,
                        "human_decision_required": True,
                    }
                if source == "NO_AUTHENTICATED_USER":
                    return {
                        "answer": "ANVI requires an authenticated user before answering plant-specific questions.",
                        "blocked": True,
                        "reason": "NO_AUTHENTICATED_USER",
                        "tenant_scoped": True,
                        "read_only": True,
                        "plc_write": False,
                        "scada_control": False,
                        "human_decision_required": True,
                    }
                return {
                    "answer": "No active authorized plant is available for this account. ANVI will not use another plant's data as a fallback.",
                    "blocked": True,
                    "reason": source or "NO_AUTHORIZED_PLANT",
                    "tenant_scoped": True,
                    "read_only": True,
                    "plc_write": False,
                    "scada_control": False,
                    "human_decision_required": True,
                }

            plant_name = "Selected plant"
            try:
                from flask import session
                plant_name = session.get("plant_name") or plant_name
            except Exception:
                pass

            return investigate(
                text,
                pid,
                plant_name,
                lambda q: current(q, *args, **kwargs),
            )
        except Exception:
            return current(text, *args, **kwargs)

    wrapped._anviqo_intelligence_orchestrated = True
    knowledge.ask_anvi = wrapped


def _plant_id():
    try:
        pid, _oid, _source = _resolve_context()
        return pid
    except Exception:
        return None


def _plant_name():
    try:
        _pid, _oid, _source = _resolve_context()
        from flask import session
        return session.get("plant_name") or session.get("plant") or "Selected plant"
    except Exception:
        return "Selected plant"


__all__ = ["install", "_query_rows", "_exact_answer", "_summary_answer"]
