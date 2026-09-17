"""ANVIQO chat context repair: derive plant from authenticated membership.

This module patches only the presentation/routing context resolver. V5/PCI
intelligence and PLC/SCADA boundaries are not changed.
"""
from __future__ import annotations


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

    # A session plant is usable only when it is still an active membership.
    # Never trust a stale plant/org pair merely because it is in the session.
    if plant_id:
        sql = (
            "SELECT m.plant_id,m.organization_id,p.name "
            "FROM anviqo_memberships m "
            "JOIN anviqo_plants p ON p.plant_id=m.plant_id "
            f"WHERE m.user_id={p} AND m.plant_id={p} "
            "AND m.status='ACTIVE' AND p.status='ACTIVE'"
        )
        with store._connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, (user_id, plant_id))
            row = cur.fetchone()
        if row:
            pid, oid = row[0], row[1]
            session["plant_id"] = pid
            session["organization_id"] = oid
            session["plant_name"] = row[2]
            session["plant_context_source"] = "AUTHORIZED_MEMBERSHIP_SESSION"
            return pid, oid, "AUTHORIZED_MEMBERSHIP_SESSION"

        session.pop("plant_id", None)
        session.pop("organization_id", None)

    sql = (
        "SELECT m.plant_id,m.organization_id,p.name "
        "FROM anviqo_memberships m "
        "JOIN anviqo_plants p ON p.plant_id=m.plant_id "
        f"WHERE m.user_id={p} AND m.status='ACTIVE' AND p.status='ACTIVE' "
        "AND m.plant_id IS NOT NULL ORDER BY p.name"
    )
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()

    if len(rows) == 1:
        pid, oid = rows[0][0], rows[0][1]
        session["plant_id"] = pid
        session["organization_id"] = oid
        session["plant_name"] = rows[0][2]
        session["plant_context_source"] = "AUTHORIZED_MEMBERSHIP_SINGLE"
        return pid, oid, "AUTHORIZED_MEMBERSHIP_SINGLE"

    if len(rows) > 1:
        return None, None, "MULTIPLE_AUTHORIZED_PLANTS"
    return None, None, "NO_AUTHORIZED_PLANT"


def resolve_pair():
    """Two-value adapter for legacy chat-stability _plant_context()."""
    pid, oid, _source = resolve()
    return pid, oid


def _install_live_answer_patch():
    """Install the final request-path answer function after v2 is loaded.

    The membership resolver already proves both the membership and ACTIVE
    plant row. The old v2 path then performed a second plant lookup and could
    reject a valid authorized context. This replacement uses the authorized
    identity directly and keeps the knowledge query bounded by plant_id.
    """
    try:
        import anvi_chat_stability_v2 as stability
        from flask import session

        if getattr(stability, "_anviqo_direct_membership_answer_patch", False):
            return True

        def membership_answer(text):
            try:
                pid, oid, source = resolve()
            except Exception as exc:
                return stability._safe(
                    "ANVI could not establish the authenticated plant context. No other plant's data was used.",
                    blocked=True,
                    reason="TENANT_CONTEXT_ERROR",
                    error_type=type(exc).__name__,
                )

            if not pid:
                if source == "MULTIPLE_AUTHORIZED_PLANTS":
                    return stability._safe(
                        "Multiple authorized plants are available for this account. ANVI requires an explicit plant context and will not guess or use another plant.",
                        blocked=True,
                        reason="MULTIPLE_AUTHORIZED_PLANTS",
                    )
                if source == "NO_AUTHENTICATED_USER":
                    return stability._safe(
                        "ANVI requires an authenticated user before answering plant-specific questions.",
                        blocked=True,
                        reason="NO_AUTHENTICATED_USER",
                    )
                return stability._safe(
                    "No active authorized plant is available for this account. ANVI will not use another plant's data as a fallback.",
                    blocked=True,
                    reason=source or "NO_AUTHORIZED_PLANT",
                )

            plant = {
                "plant_id": pid,
                "organization_id": oid,
                "name": session.get("plant_name") or "Authorized plant",
                "slug": session.get("plant_slug") or "",
                "status": "ACTIVE",
            }

            candidate = stability._candidate(text)
            # plant_id is the authoritative tenant boundary. Passing no org
            # filter avoids rejecting valid knowledge rows whose optional
            # organization metadata is NULL or stale.
            rows = (
                stability._query_rows(pid, None, identifier=candidate, limit=40)
                if candidate else
                stability._query_rows(pid, None, terms=stability._terms(text), limit=80)
            )
            return (
                stability._exact_answer(text, rows, plant)
                if candidate else
                stability._summary_answer(text, rows, plant)
            )

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
