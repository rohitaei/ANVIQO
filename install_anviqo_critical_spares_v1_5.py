#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path.cwd()
MODULE = ROOT / "pci_spares.py"

if not MODULE.exists():
    raise SystemExit("STOP: pci_spares.py not found. Nothing modified.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = MODULE.with_name(
    f"pci_spares_BEFORE_V1_5_{stamp}.py"
)

src = MODULE.read_text(encoding="utf-8")

# ------------------------------------------------------------
# SAFETY CHECK
# ------------------------------------------------------------
if "answer_spare_query" not in src:
    raise SystemExit(
        "STOP: V1.4 spare query layer not detected. "
        "V1.5 will NOT modify the module."
    )

# ------------------------------------------------------------
# DO NOT DUPLICATE EXISTING MUTATION FUNCTIONS
# Detect likely existing mutation/audit functions.
# ------------------------------------------------------------
functions = re.findall(
    r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    src,
    re.MULTILINE
)

mutation_keywords = (
    "add", "receive", "used", "remove",
    "delete", "update", "adjust", "audit"
)

existing_mutations = [
    f for f in functions
    if any(k in f.lower() for k in mutation_keywords)
]

print("=" * 70)
print("ANVIQO CRITICAL SPARES V1.5 PRE-INSTALL AUDIT")
print("=" * 70)
print("Module:", MODULE)
print()
print("Existing mutation/audit functions detected:")
for f in existing_mutations:
    print("  -", f)

print()
print("Safety boundary:")
print("  PLC WRITE       : FALSE")
print("  SCADA CONTROL   : FALSE")
print("  HUMAN DECISION  : REQUIRED")
print()

# ------------------------------------------------------------
# BACKUP
# ------------------------------------------------------------
shutil.copy2(MODULE, BACKUP)

# ------------------------------------------------------------
# V1.5 CONVERSATIONAL MANAGEMENT LAYER
#
# IMPORTANT:
# This layer DOES NOT directly modify inventory.
# It prepares a proposed action and requires explicit
# confirmation before an existing mutation function can
# be called by the host/router.
# ------------------------------------------------------------

patch = r'''

# ================================================================
# ANVIQO CRITICAL SPARES V1.5
# CONVERSATIONAL SPARE MANAGEMENT
#
# Query -> Proposal -> Human Confirmation -> Existing Mutation
#
# SAFETY:
# PLC write       = FALSE
# SCADA control   = FALSE
# Human decision  = REQUIRED
#
# This layer intentionally does NOT duplicate or replace the
# existing inventory mutation/audit functions.
# ================================================================

import re as _v15_re
from datetime import datetime as _v15_datetime


def _v15_extract_quantity(question):
    q = str(question or "")
    patterns = [
        r'\b(\d+(?:\.\d+)?)\s*(?:nos?|number|numbers|pcs?|pieces?|qty|quantity)\b',
        r'\b(?:add|receive|received|increase|put)\s+(\d+(?:\.\d+)?)\b',
    ]

    for pattern in patterns:
        m = _v15_re.search(pattern, q, _v15_re.I)
        if m:
            value = float(m.group(1))
            return int(value) if value.is_integer() else value

    return None


def _v15_action(question):
    q = str(question or "").lower()

    if any(x in q for x in (
        "add spare", "add spares",
        "new spare", "new spares",
        "receive spare", "receive spares",
        "received spare", "received spares",
        "increase stock", "increase spare"
    )):
        return "ADD"

    if any(x in q for x in (
        "use spare", "used spare",
        "consume spare", "consumed spare",
        "issue spare", "issued spare",
        "remove spare", "remove spares"
    )):
        return "USE"

    if any(x in q for x in (
        "set stock", "update stock",
        "change stock", "adjust stock"
    )):
        return "ADJUST"

    return None


def _v15_extract_tag(question):
    q = str(question or "")

    # Strong instrument tag patterns:
    # PT-303 / PT303 / MCV-205 / FSV-501 etc.
    patterns = [
        r'\b([A-Z]{2,8}-?\d{2,5}(?:/[A-Z]{2,8}-?\d{2,5})*)\b'
    ]

    for pattern in patterns:
        m = _v15_re.search(pattern, q, _v15_re.I)
        if m:
            return m.group(1).upper()

    return None


def _v15_find_existing_mutation(action):
    """
    Locate an existing mutation function without assuming its name.
    Returns function name or None.
    """
    candidates = {
        "ADD": (
            "add_spare", "add_spares",
            "receive_spare", "receive_spares",
            "record_spare"
        ),
        "USE": (
            "use_spare", "use_spares",
            "consume_spare", "issue_spare",
            "remove_spare", "remove_spares"
        ),
        "ADJUST": (
            "adjust_spare", "adjust_stock",
            "update_spare", "update_stock"
        ),
    }

    for name in candidates.get(action, ()):
        fn = globals().get(name)
        if callable(fn):
            return name

    return None


def propose_spare_mutation(question):
    """
    Converts natural-language spare management into a proposal.

    NO INVENTORY CHANGE IS PERFORMED.

    The host/router must call confirm_spare_mutation()
    only after explicit human confirmation.
    """
    action = _v15_action(question)
    quantity = _v15_extract_quantity(question)
    tag = _v15_extract_tag(question)

    if not action:
        return {
            "ok": False,
            "type": "spare_management",
            "error": "No supported spare-management action detected.",
            "human_decision_required": True,
        }

    if quantity is None or quantity <= 0:
        return {
            "ok": False,
            "type": "spare_management",
            "action": action,
            "tag": tag,
            "error": "A positive quantity is required.",
            "human_decision_required": True,
        }

    if not tag:
        return {
            "ok": False,
            "type": "spare_management",
            "action": action,
            "quantity": quantity,
            "error": "A spare tag/item identifier is required.",
            "human_decision_required": True,
        }

    mutation_function = _v15_find_existing_mutation(action)

    return {
        "ok": True,
        "type": "spare_management_proposal",
        "action": action,
        "tag": tag,
        "quantity": quantity,
        "existing_mutation_function": mutation_function,
        "confirmed": False,
        "executed": False,
        "human_decision_required": True,
        "plc_write": False,
        "scada_control": False,
        "message": (
            f"PROPOSED ACTION: {action} {quantity} spare(s) "
            f"for {tag}. No inventory has been changed. "
            f"Explicit human confirmation is required."
        ),
    }


def confirm_spare_mutation(proposal, confirmed=False):
    """
    Execute an existing mutation function ONLY after explicit
    confirmation.

    If the existing mutation API cannot be safely identified,
    nothing is changed.
    """
    if not isinstance(proposal, dict):
        return {
            "ok": False,
            "error": "Invalid spare-management proposal.",
            "executed": False,
            "human_decision_required": True,
        }

    if not confirmed:
        return {
            **proposal,
            "confirmed": False,
            "executed": False,
            "message": "Confirmation not received. No inventory changed.",
        }

    fn_name = proposal.get("existing_mutation_function")

    if not fn_name:
        return {
            **proposal,
            "confirmed": True,
            "executed": False,
            "error": (
                "No compatible existing mutation function was safely "
                "identified. No inventory changed."
            ),
            "human_decision_required": True,
        }

    fn = globals().get(fn_name)

    if not callable(fn):
        return {
            **proposal,
            "confirmed": True,
            "executed": False,
            "error": "Mutation function is unavailable. No inventory changed.",
            "human_decision_required": True,
        }

    # Do not guess an unknown function signature.
    # V1.5 intentionally stops here until the existing function's
    # contract is explicitly known.
    return {
        **proposal,
        "confirmed": True,
        "executed": False,
        "error": (
            f"Existing mutation function '{fn_name}' detected, "
            "but V1.5 will not guess its arguments. "
            "Use the existing mutation API through its defined contract."
        ),
        "human_decision_required": True,
        "safe_execution": False,
    }


def answer_spare_management(question):
    """
    Conversational entry point.

    Query questions continue through answer_spare_query().
    Mutation requests become confirmation-required proposals.
    """
    action = _v15_action(question)

    if action:
        return propose_spare_mutation(question)

    return answer_spare_query(question)

'''

# Prevent duplicate V1.5 installation.
if "ANVIQO CRITICAL SPARES V1.5" in src:
    print("V1.5 already present. No duplicate patch added.")
else:
    MODULE.write_text(src + patch, encoding="utf-8")
    print()
    print("ANVIQO CRITICAL SPARES V1.5 PATCH INSTALLED")
    print("Backup:", BACKUP)

print("=" * 70)
print("V1.5 SAFETY")
print("PLC write       : FALSE")
print("SCADA control   : FALSE")
print("Human decision  : REQUIRED")
print("Inventory auto-mutation: FALSE")
print("=" * 70)
