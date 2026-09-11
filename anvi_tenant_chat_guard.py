"""ANVIQO tenant chat isolation guard.

Keeps the frozen V5 knowledge layer intact while preventing a selected plant
from falling back to the global legacy PCI dataset when tenant knowledge is
available. This is a routing/authorization boundary, not a new reasoning
engine.

Safety: read-only; no PLC/SCADA writes; human decision required.
"""
from __future__ import annotations

import json
import re
from typing import Any

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "automatic_execution": False,
}

_TAG_RE = re.compile(r"\b(?:PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|CV|FV|XV|MCV|FSV|PCV|SOV|AI|AO|DI|DO)[-_]?\d+[A-Z0-9_-]*\b", re.I)


def _active_plant() -> str:
    try:
        from flask import has_request_context, session
        if has_request_context():
            return str(session.get("plant_id") or "").strip()
    except Exception:
        pass
    return ""


def _tenant_rows(plant_id: str) -> list[dict[str, Any]]:
    if not plant_id:
        return []
    try:
        import anvi_plant_ingestion_runtime as ingestion
        import anvi_tenant_store as store
        ingestion.init_schema()
        p = store._placeholder()
        with store._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content "
                f"FROM anviqo_plant_knowledge WHERE plant_id={p}",
                (plant_id,),
            )
            rows = cur.fetchall()
    except Exception:
        return []

    result = []
    for row in rows:
        record_type, external_id, name, area, service, asset_type, tag, parent_id, source, metadata, content = row
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        result.append({
            "record_type": str(record_type or ""),
            "external_id": str(external_id or ""),
            "name": str(name or ""),
            "area": str(area or ""),
            "service": str(service or ""),
            "asset_type": str(asset_type or ""),
            "tag": str(tag or ""),
            "parent_id": str(parent_id or ""),
            "source": str(source or ""),
            "metadata": metadata if isinstance(metadata, dict) else {},
            "content": str(content or ""),
        })
    return result


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _tenant_pci_answer(question: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Answer basic PCI/evidence questions strictly from this plant's rows."""
    q = (question or "").strip()
    ql = q.lower()
    pci_rows = [r for r in rows if r.get("record_type", "").lower() in ("instrument", "io", "pci") or r.get("tag")]
    if not pci_rows:
        return None

    requested_tags = [_norm(x) for x in _TAG_RE.findall(q)]
    if requested_tags:
        matches = [r for r in pci_rows if _norm(r.get("tag")) in requested_tags or _norm(r.get("external_id")) in requested_tags]
        if not matches:
            return {
                "answer": "I can't provide that record for the currently selected plant. The requested tag is not present in this plant's verified knowledge. I will not use another plant's data.",
                "domain": "tenant_isolation",
                "evidence": "selected plant knowledge only",
                "count": 0,
                "records": [],
                **SAFETY,
                "tenant_isolation": True,
                "plant_id": _active_plant(),
            }
        if any(x in ql for x in ("count", "how many", "number", "total")) and not any(x in ql for x in ("detail", "address", "where", "what is", "show")):
            return None
        lines = [f"ANVI found {len(matches)} verified record(s) for the selected plant:"]
        for r in matches[:20]:
            lines.append(
                f"{r.get('tag') or r.get('external_id')} — {r.get('name') or 'No description'}; "
                f"Area: {r.get('area') or 'UNKNOWN'}; Service: {r.get('service') or 'UNKNOWN'}; "
                f"Source: {r.get('source') or 'UNKNOWN'}"
            )
        return {
            "answer": "\n".join(lines),
            "domain": "pci",
            "evidence": "selected plant knowledge only",
            "count": len(matches),
            "records": matches[:20],
            **SAFETY,
            "tenant_isolation": True,
            "plant_id": _active_plant(),
        }

    if any(x in ql for x in ("how many", "count", "total", "number of")) and any(x in ql for x in ("pci", "instrument", "i/o", "io")):
        return {
            "answer": f"ANVI found {len(pci_rows)} knowledge record(s) for the currently selected plant. This response is restricted to the selected plant's tenant knowledge.",
            "domain": "pci",
            "evidence": "selected plant knowledge only",
            "count": len(pci_rows),
            "records": [],
            **SAFETY,
            "tenant_isolation": True,
            "plant_id": _active_plant(),
        }

    return None


def install() -> bool:
    try:
        import anvi_knowledge_layer as layer
        original = getattr(layer, "ask_anvi", None)
        if original is None or getattr(original, "_anviqo_tenant_guard", False):
            return False

        def tenant_aware_ask(question):
            plant_id = _active_plant()
            if not plant_id:
                return original(question)
            rows = _tenant_rows(plant_id)
            if not rows:
                return original(question)
            guarded = _tenant_pci_answer(question, rows)
            if guarded is not None:
                return guarded
            return original(question)

        tenant_aware_ask._anviqo_tenant_guard = True
        tenant_aware_ask._anviqo_original = original
        layer.ask_anvi = tenant_aware_ask
        return True
    except Exception:
        return False


INSTALLED = install()
