import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from cortexheal.server.api import app
from cortexheal.config import settings
from cortexheal.models.run import AgentRun
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.models.events import RuntimeEvent
import uuid

client = TestClient(app)

@pytest.fixture
def mock_db():
    with patch('cortexheal.server.api.get_all_runs') as m_runs, \
         patch('cortexheal.server.api.get_run') as m_run, \
         patch('cortexheal.server.api.get_incidents') as m_incidents, \
         patch('cortexheal.server.api.get_incident') as m_incident, \
         patch('cortexheal.server.api.get_events_for_run') as m_events, \
         patch('cortexheal.server.api.get_audit_events_for_run') as m_audits, \
         patch('cortexheal.server.api.protection_controller') as m_controller:
         
        yield {
            "runs": m_runs,
            "run": m_run,
            "incidents": m_incidents,
            "incident": m_incident,
            "events": m_events,
            "audits": m_audits,
            "controller": m_controller
        }

def test_get_runs(mock_db):
    run_id = str(uuid.uuid4())
    mock_db["runs"].return_value = [
        AgentRun(framework="langgraph", run_id=run_id, agent_id="test_agent", status="paused", protection_mode="ACTIVE")
    ]
    
    # Missing auth
    response = client.get("/api/runs")
    assert response.status_code == 401
    
    # Invalid auth
    response = client.get("/api/runs", headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 403
    
    # Valid auth
    response = client.get("/api/runs", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert response.status_code == 200
    resp_data = response.json()
    assert "data" in resp_data
    assert "total" in resp_data
    
    data = resp_data["data"]
    assert len(data) == 1
    assert data[0]["run_id"] == run_id
    assert data[0]["status"] == "paused"
    assert data[0]["protection_mode"] == "ACTIVE"

def test_get_incidents(mock_db):
    run_id = str(uuid.uuid4())
    inc_id = str(uuid.uuid4())
    
    mock_db["incidents"].return_value = [
        Incident(
            incident_id=inc_id, run_id=run_id, agent_id="test_agent", 
            failure_type="STUCK_LOOP", description="Test", evidence={}, status="OPEN",
            severity="HIGH", detector="stuck_loop", detector_version="1.0",
            trigger_event_id=str(uuid.uuid4()), observed_value=3, threshold=3
        )
    ]
    mock_db["run"].return_value = AgentRun(framework="langgraph", run_id=run_id, agent_id="test_agent", status="paused", protection_mode="ACTIVE")
    
    response = client.get("/api/incidents", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    resp_data = response.json()
    assert "data" in resp_data
    
    data = resp_data["data"]
    assert len(data) == 1
    assert data[0]["run_status"] == "paused"
    assert data[0]["protection_mode"] == "ACTIVE"

def test_run_timeline(mock_db):
    run_id = str(uuid.uuid4())
    inc_id = str(uuid.uuid4())
    
    mock_db["run"].return_value = AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="paused")
    
    # 1 event, 1 incident, 1 audit
    mock_db["events"].return_value = [
        RuntimeEvent(framework="langgraph", 
            event_id=str(uuid.uuid4()), run_id=run_id, agent_id="test", 
            sequence_number=1, event_type="LLM_CALL_STARTED", status="pending",
            idempotency_key="key1"
        )
    ]
    mock_db["incidents"].return_value = [
        Incident(
            incident_id=inc_id, run_id=run_id, agent_id="test", 
            failure_type="STUCK_LOOP", description="Test", evidence={}, status="OPEN",
            severity="HIGH", detector="stuck_loop", detector_version="1.0",
            trigger_event_id=str(uuid.uuid4()), observed_value=3, threshold=3
        )
    ]
    mock_db["audits"].return_value = [
        AuditEvent(event_id=str(uuid.uuid4()), run_id=run_id, action="PAUSED", actor_type="SYSTEM", actor_id="safety_gate", result="SUCCESS", reason="Test")
    ]
    
    response = client.get(f"/api/runs/{run_id}/timeline", headers={"X-API-Key": settings.get_admin_tokens()[0]})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Should be sorted by timestamp
    types = [item["type"] for item in data]
    assert sorted(types) == sorted(["event", "incident", "audit"])

def test_resume_run(mock_db):
    run_id = str(uuid.uuid4())
    mock_db["run"].return_value = AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="paused", protection_mode="ACTIVE")
    
    # Viewer should be rejected
    response = client.post(f"/api/runs/{run_id}/resume", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert response.status_code == 403
    
    # Operator should be allowed
    response = client.post(f"/api/runs/{run_id}/resume", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify controller was called correctly with operator_user
    mock_db["controller"].resume.assert_called_once_with(run_id, actor_id="operator_user", reason="Resumed via Control Plane")
