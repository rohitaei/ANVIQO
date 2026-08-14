"""
ANVIQO PCI PLANT MEMORY

Human/operator/technician experience layer.

Purpose:
    Preserve natural-language field experience without pretending
    that an operator report is automatically proven causation.

Rules:
    - Original report is preserved.
    - Read-only with respect to plant control.
    - No PLC/SCADA writes.
    - Human verification remains required.
"""

import json
import os
from datetime import datetime, timezone

MEMORY_PATH=os.path.join(
    "database","pci","pci_plant_memory.json"
)


def _load():
    if not os.path.exists(MEMORY_PATH):
        return []

    try:
        with open(MEMORY_PATH,encoding="utf-8") as f:
            data=json.load(f)

        if isinstance(data,list):
            return data

        return data.get("records",[])

    except Exception:
        return []


def _save(records):
    os.makedirs(
        os.path.dirname(MEMORY_PATH),
        exist_ok=True
    )

    with open(MEMORY_PATH,"w",encoding="utf-8") as f:
        json.dump(
            {
                "records":records,
                "read_only":True,
                "human_verification_required":True
            },
            f,
            indent=2,
            ensure_ascii=False
        )


def save_report(
    report,
    tag=None,
    source="TECHNICIAN / OPERATOR REPORT"
):
    records=_load()

    entry={
        "memory_id":len(records)+1,
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "tag":tag or "",
        "report":str(report).strip(),
        "source":source,
        "verified":False,
        "verification_status":"UNVERIFIED HUMAN REPORT",
        "read_only":True,
        "plc_write":False,
        "scada_control":False,
        "human_verification_required":True
    }

    records.append(entry)
    _save(records)

    return entry


def all_reports():
    return _load()


def search_reports(query="",tag=None):
    records=_load()

    q=str(query or "").lower()
    target=str(tag or "").lower()

    results=[]

    for r in records:
        text=(
            str(r.get("report",""))+" "+
            str(r.get("tag",""))
        ).lower()

        if target and target not in str(
            r.get("tag","")
        ).lower():
            continue

        if q and q not in text:
            continue

        results.append(r)

    return results


def similar_reports(report,tag=None):
    """
    Lightweight evidence retrieval only.
    This is NOT a new reasoning engine.
    """

    words=set(
        w.lower()
        for w in str(report).split()
        if len(w)>3
    )

    candidates=search_reports(tag=tag)

    scored=[]

    for r in candidates:
        rwords=set(
            w.lower()
            for w in str(r.get("report","")).split()
            if len(w)>3
        )

        score=len(words & rwords)

        if score:
            scored.append((score,r))

    scored.sort(
        key=lambda x:x[0],
        reverse=True
    )

    return [r for _,r in scored]


def summary(tag=None):
    records=search_reports(tag=tag)

    return {
        "count":len(records),
        "reports":records,
        "human_verified_count":sum(
            1 for r in records
            if r.get("verified") is True
        ),
        "unverified_count":sum(
            1 for r in records
            if r.get("verified") is not True
        )
    }
