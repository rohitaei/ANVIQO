"""Universal plant workbook enrichment and safety validation.

The workbook is a stable interchange format. DEMO_ONLY thresholds can drive
simulation examples only; operational assessment requires an explicit
APPROVED status, named approver, and approval reference.
"""
from __future__ import annotations
import re

def _key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

def _num(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _split_states(value):
    out=[]
    for item in re.split(r"[;,|]", str(value or "")):
        item=item.strip()
        if not item:
            continue
        try:
            number=float(item)
            out.append(int(number) if number.is_integer() else number)
        except ValueError:
            out.append(item)
    return out

def _value(row, name, default=""):
    wanted=_key(name)
    for k,v in row.items():
        if _key(k)==wanted:
            return v
    return default

def enrich_workbook_records(records):
    """Join alarm and digital semantics tabs to their matching I/O rows."""
    records=[dict(r) for r in records]
    alarms={}
    semantics={}
    for row in records:
        kind=str(row.get("record_type") or "").upper()
        tag=str(_value(row,"tag") or "").strip().upper()
        if not tag:
            continue
        if kind=="ALARM_LIMIT":
            alarms.setdefault(tag,[]).append(row)
        elif kind=="DIGITAL_SEMANTICS":
            semantics[tag]=row
    for row in records:
        if str(row.get("record_type") or "").upper() not in {"INSTRUMENT","IO","I/O","ASSET"}:
            continue
        tag=str(_value(row,"tag") or "").strip().upper()
        if not tag:
            continue
        status=str(_value(row,"configuration_status") or "PENDING_REVIEW").strip().upper()
        mode=str(_value(row,"data_mode") or "").strip().upper()
        approver=str(_value(row,"approver") or "").strip()
        approval_ref=str(_value(row,"approval_reference") or "").strip()
        limits_by_class={}
        alarm_rows=alarms.get(tag,[])
        alarm_rows_eligible=True
        expected_unit=str(_value(row,"range_unit") or "").strip().lower()
        for alarm in alarm_rows:
            cls=str(_value(alarm,"alarm_class") or "").strip().upper()
            direction=str(_value(alarm,"direction") or "").strip().upper()
            value=_num(_value(alarm,"setpoint"))
            alarm_status=str(_value(alarm,"configuration_status") or "PENDING_REVIEW").strip().upper()
            alarm_approver=str(_value(alarm,"approver") or "").strip()
            alarm_ref=str(_value(alarm,"approval_reference") or "").strip()
            alarm_demo=alarm_status=="DEMO_ONLY"
            alarm_approved=alarm_status=="APPROVED" and bool(alarm_approver and alarm_ref)
            alarm_unit=str(_value(alarm,"unit") or "").strip().lower()
            if expected_unit and alarm_unit and expected_unit != alarm_unit:
                alarm_rows_eligible=False
            if not (alarm_demo and status=="DEMO_ONLY" and mode=="SIMULATION") and not (alarm_approved and status=="APPROVED" and approver and approval_ref):
                alarm_rows_eligible=False
            if cls in {"WARNING","CRITICAL"} and direction in {"LOW","HIGH"} and value is not None:
                limits_by_class[(cls,direction)]=value
        low=_num(_value(row,"range_min"))
        high=_num(_value(row,"range_max"))
        if low is not None and high is not None and low < high:
            required={(c,d) for c in ("WARNING","CRITICAL") for d in ("LOW","HIGH")}
            if required.issubset(limits_by_class) and alarm_rows_eligible:
                demo=status=="DEMO_ONLY" and mode=="SIMULATION"
                approved=status=="APPROVED" and bool(approver and approval_ref)
                if demo or approved:
                    row["approved_engineering_limits"]={
                        "approved":True,"low":low,"high":high,
                        "warning_low":limits_by_class[("WARNING","LOW")],
                        "warning_high":limits_by_class[("WARNING","HIGH")],
                        "critical_low":limits_by_class[("CRITICAL","LOW")],
                        "critical_high":limits_by_class[("CRITICAL","HIGH")],
                        "approval_basis":"DEMO_PROFILE" if demo else "ENGINEERING_APPROVED",
                        "approver":approver,"approval_reference":approval_ref,
                        "unit":str(_value(row,"range_unit") or ""),
                    }
        digital=semantics.get(tag)
        if digital:
            ds=str(_value(digital,"configuration_status") or "PENDING_REVIEW").strip().upper()
            da=str(_value(digital,"approver") or "").strip()
            dr=str(_value(digital,"approval_reference") or "").strip()
            demo=ds=="DEMO_ONLY" and mode=="SIMULATION"
            approved=ds=="APPROVED" and bool(da and dr)
            normal=_split_states(_value(digital,"normal_states"))
            alarm=_split_states(_value(digital,"alarm_states"))
            if (demo or approved) and normal and alarm and not set(normal).intersection(alarm):
                row["approved_signal_semantics"]={
                    "approved":True,"normal_states":normal,"alarm_states":alarm,
                    "approval_basis":"DEMO_PROFILE" if demo else "ENGINEERING_APPROVED",
                    "approver":da,"approval_reference":dr,
                }
    return records

__all__=["enrich_workbook_records"]
