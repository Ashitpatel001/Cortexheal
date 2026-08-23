import pytest
import uuid
import csv
import io
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from cortexheal.server.api import app
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.models.protection import AuditEvent
from cortexheal.models.recovery import RecoveryPlan
from cortexheal.storage.postgres import (
    save_incident, save_run, save_audit_event, save_recovery_plan, init_db
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_audit_export_rbac():
    viewer_headers = {"X-API-Key": "dev-viewer-key"}
    operator_headers = {"X-API-Key": "dev-operator-key"}
    admin_headers = {"X-API-Key": "dev-admin-key"}

    # Viewer should be rejected
    res = client.get("/api/audit/export", headers=viewer_headers)
    assert res.status_code == 403

    # Operator should be accepted
    res = client.get("/api/audit/export", headers=operator_headers)
    assert res.status_code == 200

    # Admin should be accepted
    res = client.get("/api/audit/export", headers=admin_headers)
    assert res.status_code == 200

def test_audit_export_json_format():
    run_id = f"export_run_{uuid.uuid4().hex[:6]}"
    inc_id = str(uuid.uuid4())
    
    save_run(AgentRun(run_id=run_id, agent_id="compliance_agent", framework="langgraph", status="paused"))
    save_incident(Incident(
        incident_id=inc_id,
        run_id=run_id,
        agent_id="compliance_agent",
        failure_type="STUCK_LOOP",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"repetitions": 5, "tool": "search_db"},
        observed_value=5,
        threshold=4,
        description="Repetitive loop detected",
        status="OPEN"
    ))
    save_audit_event(AuditEvent(
        run_id=run_id,
        incident_id=inc_id,
        action="PAUSED",
        actor_type="SYSTEM",
        actor_id="safety_gate",
        result="SUCCESS",
        reason="Triggered circuit breaker"
    ))

    res = client.get(f"/api/audit/export?format=json&agent_id=compliance_agent", headers={"X-API-Key": "dev-operator-key"})
    assert res.status_code == 200
    data = res.json()
    assert "total_records" in data
    assert "exported_at" in data
    assert "records" in data
    assert data["filters"]["agent_id"] == "compliance_agent"

    matching = [r for r in data["records"] if r["run_id"] == run_id]
    assert len(matching) >= 1
    rec = matching[0]
    assert rec["agent_id"] == "compliance_agent"
    assert rec["failure_type"] == "STUCK_LOOP"
    assert rec["severity"] == "HIGH"
    assert rec["detector"] == "stuck_loop"
    assert rec["audit_action"] == "PAUSED"
    assert rec["audit_actor_type"] == "SYSTEM"

def test_audit_export_csv_format():
    res = client.get("/api/audit/export?format=csv", headers={"X-API-Key": "dev-admin-key"})
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=\"cortexheal_audit_export_" in res.headers["content-disposition"]

    # Parse CSV content
    content = res.text
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames
    assert "incident_id" in headers
    assert "run_id" in headers
    assert "agent_id" in headers
    assert "failure_type" in headers
    assert "severity" in headers
    assert "audit_action" in headers
    assert "audit_actor_type" in headers

def test_audit_export_filtering():
    run_a = f"run_a_{uuid.uuid4().hex[:6]}"
    run_b = f"run_b_{uuid.uuid4().hex[:6]}"

    save_run(AgentRun(run_id=run_a, agent_id="agent_alpha", framework="langgraph", status="paused"))
    save_run(AgentRun(run_id=run_b, agent_id="agent_beta", framework="langgraph", status="paused"))

    save_incident(Incident(
        incident_id=str(uuid.uuid4()),
        run_id=run_a,
        agent_id="agent_alpha",
        failure_type="STUCK_LOOP",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"tool": "sql_query"},
        observed_value=4,
        threshold=4,
        description="Alpha stuck loop",
        status="OPEN"
    ))
    save_incident(Incident(
        incident_id=str(uuid.uuid4()),
        run_id=run_b,
        agent_id="agent_beta",
        failure_type="BUDGET_EXCEEDED",
        severity="CRITICAL",
        detector="budget_detector",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"cost": 1.50},
        observed_value=1.50,
        threshold=1.00,
        description="Beta budget overrun",
        status="OPEN"
    ))

    # Filter by failure_type=BUDGET_EXCEEDED
    res = client.get("/api/audit/export?format=json&failure_type=BUDGET_EXCEEDED", headers={"X-API-Key": "dev-operator-key"})
    assert res.status_code == 200
    records = res.json()["records"]
    assert all(r["failure_type"] == "BUDGET_EXCEEDED" for r in records)
    assert any(r["run_id"] == run_b for r in records)
    assert not any(r["run_id"] == run_a for r in records)

    # Filter by agent_id=agent_alpha
    res = client.get("/api/audit/export?format=json&agent_id=agent_alpha", headers={"X-API-Key": "dev-operator-key"})
    assert res.status_code == 200
    records = res.json()["records"]
    assert all(r["agent_id"] == "agent_alpha" for r in records)
