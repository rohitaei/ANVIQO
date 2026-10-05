        # engineering-tag requests such as "Show simulated change on PT-303".
        ql=q.lower()
        v2_change_request = any(term in ql for term in (
            "what changed",
            "what has changed",
            "show changes",
            "recent change",
            "recent changes",
            "any change",
            "any changes",
            "show simulated change",
            "simulated change",
            "simulation change",
            "simulate change",
            "show simulation",
        )) or (("simulation" in ql or "simulated" in ql) and "change" in ql)
        if v2_change_request:
            # Plain plant-level "What Changed?" must use the selected
            # plant's deterministic simulation snapshot before any
            # equipment-memory/event-correlation route. This prevents a
            # previous PT-303 (or any other tag) conversation from changing
            # the meaning of a later generic What Changed request.
            plain_what_changed = not _re.search(
                r"\b(?:PT|FT|TT|LT|AT|CV|FV|XV|PIC|FIC|TIC|LIC)[-_ ]?\d+\b",
                q.upper(),
            ) and "simulation" not in ql and "simulated" not in ql
            if plain_what_changed:
                try:
                    from anvi_chat_stability_v2 import _selected_pci_snapshot
                    snapshot = _selected_pci_snapshot() or {}
                    points = [
                        p for p in (snapshot.get("points") or [])
                        if isinstance(p, dict)
                    ]
                    changed_points = [p for p in points if p.get("changed")]
                    event_points = [p for p in points if p.get("event_active")]
                    lines = [
                        "ANVI — What Changed (SIMULATION)",
                        f"Verified changed points/events in the selected plant: {len(changed_points)} changed points | {len(event_points)} active events."
                    ]
                    for p in changed_points[:12]:
                        tag = p.get("tag") or p.get("name") or "UNKNOWN"
                        desc = p.get("description") or p.get("name") or "No description"
                        value = p.get("value", "N/A")
                        state = p.get("state", "UNKNOWN")
                        lines.append(f"{tag} — {desc} — Current value: {value} — State: {state}.")
                    if not changed_points and not event_points:
                        lines.extend([
                            "No verified simulation change/event evidence is currently recorded for the selected plant.",
                            "ANVI will not invent a change.",
                        ])
                    lines.extend([
                        "Evidence source: PCI DEMO STREAM. This is simulation data, not live plant telemetry.",
                        "Safety: ANVI is read-only; no PLC/SCADA write. Human decision required.",
                    ])
                    return _regression_safety_contract(q, {
                        "answer": "\n".join(lines),
                        "domain": "event_correlation",
                        "evidence": "PCI DEMO STREAM",
                        "simulation": True,
                        "read_only": True,