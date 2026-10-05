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
            # V2 Command Centre intents must be handled before the generic
            # knowledge search. These questions ask for the selected plant's
            # live/simulated intelligence, not for a matching text record.
            # The snapshot is tenant-scoped and cannot fall back to another plant.
            try:
                snapshot = stability._selected_pci_snapshot()
                low_intent = str(text or "").strip().lower()
                if any(x in low_intent for x in (
                    "current plant health", "what is the current plant health",
                    "plant health", "overall plant health", "health of the plant"
                )):
                    if str(snapshot.get("mode", "")).upper() == "SIMULATION":
                        score = snapshot.get("plant_health_score")
                        if score is not None:
                            if float(score) >= 90: condition = "BROADLY HEALTHY"
                            elif float(score) >= 80: condition = "HEALTHY WITH ATTENTION AREAS"
                            elif float(score) >= 60: condition = "DEGRADED"
                            else: condition = "CRITICAL"
                        else:
                            condition = "INSUFFICIENT EVIDENCE"
                        return stability._safe(
                            "ANVI — Current Plant Health (SIMULATION)\\n"
                            f"Overall condition: {condition}.\\n"
                            f"Health score: {score}%.\\n"
                            f"Healthy: {snapshot.get('healthy', 0)} | Warning: {snapshot.get('warning', 0)} | Critical: {snapshot.get('critical', 0)}.\\n"
                            f"Changed points: {snapshot.get('changed', 0)} | Active simulated events: {snapshot.get('active_events', 0)}.\\n"
                            "Evidence source: PCI DEMO STREAM. This is simulation data, not live plant telemetry.\\n"
                            "Safety: ANVI is read-only; no PLC/SCADA write. Human decision required.",
                            domain="plant_health", evidence_status="EVIDENCE_AVAILABLE",
                            evidence_mode="SIMULATION", plant_id=pid, plant_name=plant.get("name")
                        )
                if any(x in low_intent for x in (
                    "show active alarms", "active alarms", "current active alarms", "show alarms"
                )):
                    points = [
                        p for p in (snapshot.get("points") or [])
                        if isinstance(p, dict) and p.get("event_active")
                        and str(p.get("state", "")).upper() in ("WARNING", "CRITICAL")
                    ]
                    lines = [
                        "ANVI — Active Alarms (SIMULATION)",
                        f"Active simulated alarms/events: {len(points)}."
                    ]
                    for p in sorted(points, key=lambda p: (
                        str(p.get("state", "")).upper() != "CRITICAL",
                        str(p.get("tag", ""))
                    ))[:12]:
                        lines.append(
                            f"{p.get('tag', 'UNKNOWN')} — {p.get('state', 'UNKNOWN')} — "
                            f"{p.get('description') or p.get('name') or 'No description'} — "
                            f"Area: {p.get('area') or 'UNKNOWN'}."
                        )
                    if not points:
                        lines.append("No active simulated alarm/event points were detected in this snapshot.")
                    lines += [
                        "Evidence source: PCI DEMO STREAM. This is simulation data, not live alarm history.",
                        "Safety: ANVI is read-only; no PLC/SCADA write. Human decision required."
                    ]
                    return stability._safe(
                        "\\n".join(lines), domain="alarms",
                        evidence_status="EVIDENCE_AVAILABLE", evidence_mode="SIMULATION",
                        plant_id=pid, plant_name=plant.get("name")
                    )
                if any(x in low_intent for x in (
                    "show critical equipment", "critical equipment", "critical points", "critical tags"
                )):
                    points = [
                        p for p in (snapshot.get("points") or [])
                        if isinstance(p, dict) and str(p.get("state", "")).upper() == "CRITICAL"
                    ]
                    lines = [
                        "ANVI — Critical Equipment / Points (SIMULATION)",
                        f"Critical points: {len(points)}."
                    ]
                    for p in points[:15]:
                        lines.append(
                            f"{p.get('tag', 'UNKNOWN')} — {p.get('value', 'N/A')} — "
                            f"{p.get('description') or p.get('name') or 'No description'} — "
                            f"Area: {p.get('area') or 'UNKNOWN'}."
                        )
                    if not points:
                        lines.append("No critical points were detected in this snapshot.")
                    lines += [
                        "Evidence source: PCI DEMO STREAM. This is simulation data, not live equipment telemetry.",
                        "Safety: ANVI is read-only; no PLC/SCADA write. Human decision required."
                    ]
                    return stability._safe(
                        "\\n".join(lines), domain="critical_equipment",
                        evidence_status="EVIDENCE_AVAILABLE", evidence_mode="SIMULATION",
                        plant_id=pid, plant_name=plant.get("name")
                    )

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

        # Tenant-scoped verified PCI adapter: when the selected plant has an
        # explicit binding to the bundled verified PCI dataset, expose that evidence
        # through the existing frozen resolver. Never use the registry as a global
        # fallback; unbound plants remain tenant-knowledge-only.
        if not getattr(stability, "_anviqo_verified_pci_adapter_patch", False):
            original_pci_resolve_rows = stability._pci_resolve_rows
            def tenant_pci_resolve_rows(plant_id, organization_id, query):
                rows = original_pci_resolve_rows(plant_id, organization_id, query)
                if rows:
                    return rows
                try:
                    import anvi_verified_pci_adapter as verified_pci
                    return verified_pci.resolve_for_bound_plant(
                        plant_id, organization_id, query
                    )
                except Exception as exc:
                    print(f"ANVIQO_VERIFIED_PCI_ADAPTER_ERROR error={exc!r}", flush=True)
                    return []
            stability._pci_resolve_rows = tenant_pci_resolve_rows
            stability._anviqo_verified_pci_adapter_patch = True

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
