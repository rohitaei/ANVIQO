"""
ANVIQO — FULL ANVI PRODUCT FACADE

Single customer-facing intelligence facade.
Existing V5 intelligence remains authoritative.
Read-only / human-decision safety boundary.
"""

from datetime import datetime

VERSION = "ANVIQO FULL ANVI 1.0"

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}


class ANVI:
    def __init__(self):
        self.product = "ANVIQO"
        self.version = VERSION

    def status(self):
        return {
            "product": self.product,
            "version": self.version,
            "status": "READY",
            "intelligence_core": "V5 FROZEN",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "safety": SAFETY,
        }

    def ask(self, question):
        question = str(question or "").strip()

        if not question:
            return self._response(
                "Please ask ANVI a plant, equipment, instrumentation, "
                "maintenance, event, shift, or management question."
            )

        try:
            from anvi_knowledge_layer import ask_anvi
            result = ask_anvi(question)

            if isinstance(result, dict):
                result.setdefault("product", "ANVIQO")
                result.setdefault("assistant", "ANVI")
                result["read_only"] = True
                result["plc_write"] = False
                result["scada_control"] = False
                result["human_decision_required"] = True
                return result

            return self._response(str(result))

        except Exception as exc:
            return {
                "answer": "ANVI knowledge service is temporarily unavailable.",
                "error": str(exc),
                "product": "ANVIQO",
                "assistant": "ANVI",
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_decision_required": True,
            }

    def pci(self, question):
        from pci_universal_resolver import resolve
        rows, mode = resolve(question)

        return {
            "mode": mode,
            "count": len(rows),
            "records": rows,
            "evidence": "verified PCI database",
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    def plant_snapshot(self):
        try:
            from pci_live_simulator import get_live_pci_snapshot
            snapshot = get_live_pci_snapshot()
            snapshot["product"] = "ANVIQO"
            snapshot["assistant"] = "ANVI"
            snapshot["safety"] = SAFETY
            return snapshot
        except Exception as exc:
            return {
                "status": "ERROR",
                "error": str(exc),
                "safety": SAFETY,
            }

    def equipment(self, tag):
        from equipment_database import get_equipment
        return {
            "equipment": tag,
            "identity": get_equipment(tag),
            "read_only": True,
        }

    def _response(self, answer):
        return {
            "answer": answer,
            "product": "ANVIQO",
            "assistant": "ANVI",
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        }


anvi = ANVI()


def ask(question):
    return anvi.ask(question)


def system_status():
    return anvi.status()


if __name__ == "__main__":
    print("=" * 64)
    print("ANVIQO — FULL ANVI PRODUCT")
    print("=" * 64)
    print("VERSION :", VERSION)
    print("STATUS  :", "READY")
    print("CORE    :", "V5 FROZEN")
    print("SAFETY  :", SAFETY)
