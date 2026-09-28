from flask import Flask, session

import v2_command_centre_stream as stream


def _ctx(plant_id="plant-a", organization_id="org-a"):
    app = Flask(__name__)
    app.secret_key = "test"
    ctx = app.test_request_context("/")
    ctx.__enter__()
    session["authenticated"] = True
    session["plant_id"] = plant_id
    session["organization_id"] = organization_id
    return ctx


def test_stream_uses_only_selected_plant_and_explicit_events(monkeypatch):
    rows = [
        {
            "plant_id": "plant-a",
            "tag": "TIC-101A",
            "source": "plant-a-events",
            "external_id": "E1",
            "metadata": {
                "event_type": "ALARM",
                "timestamp": "2026-09-28T08:00:00Z",
                "message": "Temperature alarm",
            },
        },
        {
            "plant_id": "plant-b",
            "tag": "TIC-101A",
            "metadata": {
                "event_type": "ALARM",
                "message": "Other plant",
            },
        },
        {
            "plant_id": "plant-a",
            "tag": "TIC-101A",
            "metadata": {
                "change_type": "VALUE_CHANGE",
                "previous": 10,
                "current": 12,
                "direction": "INCREASED",
            },
        },
    ]
    monkeypatch.setattr(stream, "_metadata", lambda row: row.get("metadata", {}))
    monkeypatch.setattr("anvi_tenant_chat_boundary._rows", lambda *a, **k: rows)
    ctx = _ctx()
    try:
        result = stream.build_command_centre_stream("TIC-101A", "TIC-101A")
    finally:
        ctx.__exit__(None, None, None)

    assert result["scope"] == "SELECTED_PLANT_ONLY"
    assert result["plant_id"] == "plant-a"
    assert len(result["events"]) == 1
    assert len(result["changes"]) == 1
    assert result["correlation"]["causation_claimed"] is False
    assert result["safety"]["plc_write"] is False


def test_stream_does_not_invent_events_or_changes(monkeypatch):
    monkeypatch.setattr("anvi_tenant_chat_boundary._rows", lambda *a, **k: [
        {"plant_id": "plant-a", "tag": "P-101", "name": "Pump"},
    ])
    ctx = _ctx()
    try:
        result = stream.build_command_centre_stream("P-101", "P-101")
    finally:
        ctx.__exit__(None, None, None)

    assert result["status"] == "NO DATA"
    assert result["events"] == []
    assert result["changes"] == []
    assert result["change_status"] == "NO CHANGE BASELINE"
