"""Regression coverage for the final tenant-membership chat wrapper."""
import sys
from types import SimpleNamespace

from flask import Flask


def test_hyphenated_critical_point_prompt_uses_complete_high_criticality_report(monkeypatch):
    import anvi_tenant_context_autofix as context_fix

    points = [
        {"tag": tag, "description": description, "area": "VRM / MILL",
         "state": "HIGH_CRITICALITY", "metadata": {"criticality": "HIGH"}}
        for tag, description in [
            ("AT_201", "Mill inlet O2"),
            ("AT_202", "Mill inlet CO"),
            ("LT_302", "Mill bed height"),
            ("PT_303", "Mill outlet gas pressure"),
        ]
    ]
    fake_stability = SimpleNamespace(
        _is_data_question=lambda _text: False,
        _pci_resolve_rows=lambda *_args: [],
        _safe=lambda answer, **extra: {"answer": answer, **extra},
        _selected_pci_snapshot=lambda: {"mode": "ONBOARDING_DATA", "points": []},
        _selected_critical_point_snapshot=lambda _pid, _oid: {
            "mode": "ONBOARDING_DATA",
            "source": "SELECTED_PLANT_HIGH_CRITICALITY_PCI_KNOWLEDGE",
            "critical_count": 4,
            "points": points,
        },
    )
    monkeypatch.setitem(sys.modules, "anvi_chat_stability_v2", fake_stability)
    monkeypatch.setattr(
        context_fix, "resolve",
        lambda: ("plant-selected", "org-selected", "AUTHORIZED_MEMBERSHIP_SESSION"),
    )
    assert context_fix._install_live_answer_patch() is True

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/api/ask", method="POST"):
        from flask import session
        session["user_id"] = "user-1"
        session["plant_id"] = "plant-selected"
        session["plant_name"] = "Primary Plant"
        result = fake_stability._answer(
            "Reconcile the critical-point count. Return every unique critical tag "
            "from the selected plant, without truncation. Include measured value, "
            "unit, timestamp, configured limit, evidence, severity reason and "
            "recommended human action."
        )

    assert result["domain"] == "critical_equipment"
    assert result["count"] == 4
    for tag in ("AT_201", "AT_202", "LT_302", "PT_303"):
        assert tag in result["answer"]
    assert "Configured limit: UNAVAILABLE" in result["answer"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False
