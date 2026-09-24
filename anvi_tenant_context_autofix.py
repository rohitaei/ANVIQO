"""ANVIQO chat context repair: derive plant from authenticated membership.

This module patches only the presentation/routing context resolver. V5/PCI
intelligence and PLC/SCADA boundaries are not changed.
"""
from __future__ import annotations
import re


def resolve():
    from flask import session
    plant_id = str(session.get("plant_id") or "").strip()
    user_id = str(session.get("user_id") or "").strip()
    if not user_id:
        return None, None, "NO_AUTHENTICATED_USER"
    import anvi_tenant_store as store
    if not store.enabled():
        return None, None, "TENANT_STORE_UNAVAILABLE"
    store.init_schema()
    p = store._placeholder()
    if plant_id:
        sql = (
            "SELECT m.plant_id,m.organization_id,p.name FROM anviqo_memberships m "
            "JOIN anviqo_plants p ON p.plant_id=m.plant_id "
            f"WHERE m.user_id={p} AND m.plant_id={p} "
            "AND m.status='ACTIVE' AND p.status='ACTIVE'"
        )
        with store._connect() as conn:
            cur = conn.cursor(); cur.execute(sql, (user_id, plant_id)); row = cur.fetchone()
        if row:
            pid, oid = row[0], row[1]
            session["plant_id"] = pid; session["organization_id"] = oid
            session["plant_name"] = row[2]; session["plant_context_source"] = "AUTHORIZED_MEMBERSHIP_SESSION"
            return pid, oid, "AUTHORIZED_MEMBERSHIP_SESSION"
        session.pop("plant_id", None); session.pop("organization_id", None)
    sql = (
        "SELECT m.plant_id,m.organization_id,p.name FROM anviqo_memberships m "
        "JOIN anviqo_plants p ON p.plant_id=m.plant_id "
        f"WHERE m.user_id={p} AND m.status='ACTIVE' AND p.status='ACTIVE' "
        "AND m.plant_id IS NOT NULL ORDER BY p.name"
    )
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute(sql, (user_id,)); rows = cur.fetchall()
    if len(rows) == 1:
        pid, oid = rows[0][0], rows[0][1]
        session["plant_id"] = pid; session["organization_id"] = oid
        session["plant_name"] = rows[0][2]; session["plant_context_source"] = "AUTHORIZED_MEMBERSHIP_SINGLE"
        return pid, oid, "AUTHORIZED_MEMBERSHIP_SINGLE"
    if len(rows) > 1:
        return None, None, "MULTIPLE_AUTHORIZED_PLANTS"
    return None, None, "NO_AUTHORIZED_PLANT"


def resolve_pair():
    pid, oid, _source = resolve()
    return pid, oid


def _install_live_answer_patch():
    """Install the final request-path answer after Flask is available."""
    try:
        import anvi_chat_stability_v2 as stability
        if getattr(stability, "_anviqo_direct_membership_answer_patch", False):
            return True

        # Universal tag-like questions such as MFT_680 must enter the same
        # tenant answer path even when their prefix is not in the legacy list.
        original_data_question = stability._is_data_question
        if not getattr(stability, "_anviqo_universal_tag_question_patch", False):
            def universal_data_question(text):
                if original_data_question(text):
                    return True
                return bool(re.search(r"\b[A-Za-z]{2,12}[-_ ]?\d{1,6}\b", str(text or "")))
            stability._is_data_question = universal_data_question
            stability._anviqo_universal_tag_question_patch = True

        def membership_answer(text):
            from flask import session
            try:
                pid, oid, source = resolve()
            except Exception as exc:
                return stability._safe("ANVI could not establish the authenticated plant context. No other plant's data was used.", blocked=True, reason="TENANT_CONTEXT_ERROR", error_type=type(exc).__name__)
            if not pid:
                if source == "MULTIPLE_AUTHORIZED_PLANTS":
                    return stability._safe("Multiple authorized plants are available for this account. ANVI requires an explicit plant context and will not guess or use another plant.", blocked=True, reason="MULTIPLE_AUTHORIZED_PLANTS")
                if source == "NO_AUTHENTICATED_USER":
                    return stability._safe("ANVI requires an authenticated user before answering plant-specific questions.", blocked=True, reason="NO_AUTHENTICATED_USER")
                return stability._safe("No active authorized plant is available for this account. ANVI will not use another plant's data as a fallback.", blocked=True, reason=source or "NO_AUTHORIZED_PLANT")
            plant = {
                "plant_id": pid,
                "organization_id": oid,
                "name": session.get("plant_name") or "Authorized plant",
                "slug": session.get("plant_slug") or "",
                "status": "ACTIVE",
            }
            # Reuse the authoritative critical-spares intelligence before the
            # plant-knowledge resolver. This keeps "spares of MCV" and exact
            # spare-tag questions on the existing spare engine instead of
            # incorrectly treating them as plant-knowledge searches.
            low = str(text or "").lower()
            spare_intent = any(x in low for x in (
                "spare", "spares", "inventory", "stock", "indent"
            ))
            if spare_intent:
                try:
                    import pci_spares
                    result = pci_spares.answer_spare_management(text)
                    if isinstance(result, dict):
                        result.setdefault("plant_id", pid)
                        result.setdefault("plant_name", plant.get("name"))
                        result.setdefault("human_decision_required", True)
                        result.setdefault("plc_write", False)
                        result.setdefault("scada_control", False)
                        return result
                except Exception as exc:
                    print(f"ANVIQO_SPARE_ROUTING_ERROR error={exc!r}", flush=True)

            candidate = stability._candidate(text)
            # Keep the universal PCI resolver on the actual live request path.
            # Resolver input remains tenant-scoped. Plant ID is the
            # authorization boundary; organization_id is retried without the
            # redundant filter so older/imported rows remain readable when
            # their organization metadata is stale. No cross-plant fallback
            # is possible because every query still requires this plant_id.
            if candidate:
                rows = stability._pci_resolve_rows(pid, oid, candidate)
                if not rows and oid:
                    rows = stability._pci_resolve_rows(pid, None, candidate)
                if not rows:
                    rows = stability._query_rows(pid, oid, identifier=candidate, limit=40)
                if not rows and oid:
                    rows = stability._query_rows(pid, None, identifier=candidate, limit=40)
            else:
                rows = stability._query_rows(pid, oid, terms=stability._terms(text), limit=80)
                if not rows and oid:
                    rows = stability._query_rows(pid, None, terms=stability._terms(text), limit=80)
            return stability._exact_answer(text, rows, plant) if candidate else stability._summary_answer(text, rows, plant)

        stability._answer = membership_answer
        stability._anviqo_direct_membership_answer_patch = True
        return True
    except Exception as exc:
        print(f"ANVIQO_DIRECT_MEMBERSHIP_ANSWER_PATCH_ERROR error={exc!r}", flush=True)
        return False


def install():
    try:
        import anvi_tenant_chat_boundary as boundary
        boundary._session_context = resolve
    except Exception:
        return False
    try:
        import anvi_chat_stability_v2 as _chat_stability
        _chat_stability._plant_context = resolve_pair
        _chat_stability._anviqo_membership_context_patch = True
    except Exception as exc:
        print(f"ANVIQO_CHAT_STABILITY_CONTEXT_PATCH_ERROR error={exc!r}", flush=True)
    _install_live_answer_patch()
    return True


install()
