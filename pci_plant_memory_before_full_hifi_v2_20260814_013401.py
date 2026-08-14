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
import re
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



def _tokens(text):
    text=str(text or "").lower()

    # Preserve engineering identifiers such as CV-101 / LP_1_Healthy
    ids=re.findall(
        r"\b[a-z]{1,12}[-_][a-z0-9_]+\b",
        text
    )

    words=re.findall(
        r"\b[a-z0-9]{3,}\b",
        text
    )

    stop={
        "have","seen","this","before","for",
        "the","and","was","were","with",
        "what","which","does","did","been",
        "from","that","into","after","when"
    }

    return set(
        x for x in (ids+words)
        if x not in stop
    )


def similar_reports(report,tag=None):
    """
    Retrieve previous human experience.

    Priority:
      1. Exact engineering tag match.
      2. Meaningful keyword overlap.

    This is retrieval only. It is NOT a new reasoning engine
    and does not establish causation.
    """

    records=_load()

    q=str(report or "")
    q_tokens=_tokens(q)

    requested_tag=str(tag or "").strip().lower()

    scored=[]

    for r in records:

        r_tag=str(
            r.get("tag","")
        ).strip().lower()

        r_text=str(
            r.get("report","")
        )

        r_tokens=_tokens(r_text)

        score=0

        # Strongest evidence: exact equipment/tag match.
        if requested_tag and r_tag:
            if requested_tag == r_tag:
                score += 100

        # Keyword overlap.
        overlap=q_tokens & r_tokens

        score += min(
            len(overlap)*5,
            50
        )

        if score > 0:
            scored.append(
                (score,r)
            )

    scored.sort(
        key=lambda x: (
            x[0],
            x[1].get("memory_id",0)
        ),
        reverse=True
    )

    return [
        r for _,r in scored
    ]


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
