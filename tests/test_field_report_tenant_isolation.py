from flask import Flask, session

import anvi_field_report
import field_report_runtime


def test_authenticated_field_report_is_saved_only_to_tenant_store(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    calls = {"local": 0, "tenant": []}

    def local_memory_must_not_be_written(**kwargs):
        calls["local"] += 1
        raise AssertionError("Authenticated tenant report reached shared local Plant Memory")

    def create_memory(**kwargs):
        return {
            "memory_id": "PM-TENANT-001",
            "verification_status": "PENDING_VERIFICATION",
            **kwargs,
        }

    def tenant_upsert(record):
        calls["tenant"].append(record)
        return True

    monkeypatch.setattr("plant_memory.create_conversational_memory", local_memory_must_not_be_written)
    monkeypatch.setattr("plant_memory.create_memory", create_memory)
    monkeypatch.setattr("anvi_neon_store.upsert_field_report", tenant_upsert)

    with app.test_request_context("/api/field_report"):
        session.update({
            "authenticated": True,
            "user_id": "user-1",
            "organization_id": "org-1",
            "plant_id": "plant-1",
        })
        result = anvi_field_report.store_field_report(
            "PT-303 Observation: no indication. Finding: fuse blown. "
            "Maintenance action: replaced fuse. Outcome: signal returned to normal."
        )

    assert calls["local"] == 0
    assert len(calls["tenant"]) == 1
    stored = calls["tenant"][0]
    assert stored["plant_id"] == "plant-1"
    assert stored["organization_id"] == "org-1"
    assert stored["verification_status"] == "PENDING_VERIFICATION"
    assert result["status"] == "PENDING_VERIFICATION"


def test_authenticated_field_report_fails_closed_if_tenant_store_unavailable(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "plant_memory.create_memory",
        lambda **kwargs: {"memory_id": "PM-TENANT-002", **kwargs},
    )
    monkeypatch.setattr(
        "plant_memory.create_conversational_memory",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("shared store used")),
    )
    monkeypatch.setattr("anvi_neon_store.upsert_field_report", lambda record: False)

    with app.test_request_context("/api/field_report"):
        session.update({
            "authenticated": True,
            "user_id": "user-1",
            "organization_id": "org-1",
            "plant_id": "plant-1",
        })
        try:
            anvi_field_report.store_field_report("PT-303 Observation: no indication.")
        except RuntimeError as exc:
            assert "Tenant field-report store is unavailable" in str(exc)
        else:
            raise AssertionError("Tenant report save should fail closed")


def test_authenticated_report_query_without_selected_plant_never_reads_shared_memory(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"

    def forbidden_shared_read(**kwargs):
        raise AssertionError("Shared Plant Memory must not be queried for authenticated users")

    monkeypatch.setattr("plant_memory.search_all_memory", forbidden_shared_read)

    with app.test_request_context("/api/ask"):
        session.update({
            "authenticated": True,
            "user_id": "user-1",
            "organization_id": "org-1",
        })
        result = field_report_runtime.answer_field_report_query("Show field report PT-303")

    assert result["status"] == "BLOCKED"
    assert result["evidence_status"] == "NO_AUTHORIZED_PLANT"
    assert "No shared or other-plant" in result["answer"]


def test_authenticated_report_query_uses_tenant_store_not_shared_memory(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"

    def forbidden_shared_read(**kwargs):
        raise AssertionError("Shared Plant Memory must not be queried for authenticated tenants")

    tenant_report = {
        "report_id": "PM-TENANT-003",
        "memory_id": "PM-TENANT-003",
        "tag": "PT-303",
        "equipment": "PT-303",
        "source": "technician field report",
        "observation": "No indication",
        "finding": "Fuse blown",
        "maintenance_action": "Fuse replaced",
        "outcome": "Signal restored",
        "verification_status": "PENDING_VERIFICATION",
    }
    monkeypatch.setattr("plant_memory.search_all_memory", forbidden_shared_read)
    monkeypatch.setattr(
        "field_report_persistent_bridge._field_reports_from_neon",
        lambda tag="", limit=20: [tenant_report],
    )

    with app.test_request_context("/api/ask"):
        session.update({
            "authenticated": True,
            "user_id": "user-1",
            "organization_id": "org-1",
            "plant_id": "plant-1",
        })
        result = field_report_runtime.answer_field_report_query("Show field report for PT-303")

    assert result["status"] == "OK"
    assert result["verification_status"] == "PENDING_VERIFICATION"
    assert "Fuse blown" in result["answer"]
