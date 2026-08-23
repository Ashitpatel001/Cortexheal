import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.server.api import app
from cortexheal.config import settings
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class AgentState(TypedDict, total=False):
    input: str
    count: int
    run_id: str

def agent_node(state: AgentState):
    from cortexheal.models.events import RuntimeEvent
    from cortexheal.runtime.collector import collector
    current_run_id = state.get("run_id", "e2e_run_123")
    # Emit an event simulating a tool call
    event = RuntimeEvent(
        run_id=current_run_id,
        agent_id="e2e_agent",
        framework="langgraph",
        event_type="TOOL_CALL_COMPLETED",
        sequence_number=state["count"],
        idempotency_key=f"tool_{current_run_id}_{state['count']}",
        status="success",
        tool="test_tool",
        arguments_hash="hash_args",
        response_hash="hash_resp"
    )
    collector.ingest_event(event)
    
    time.sleep(0.1)  # Allow background telemetry worker to process events
    return {"count": state["count"] + 1, "run_id": current_run_id}

def should_continue(state: AgentState):
    if state["count"] > 10:
        return END
    return "safety_gate"

@pytest.fixture(autouse=True)
def mock_db():
    from cortexheal.models.run import AgentRun
    db_state = {
        "runs": {},
        "incidents": [],
        "events": [],
        "audits": [],
        "plans": {}
    }
    
    def mock_get_run(run_id):
        return db_state["runs"].get(run_id)
        
    def mock_save_run(run):
        db_state["runs"][run.run_id] = run
        return True
        
    def mock_save_event(event):
        db_state["events"].append(event)
        return True
        
    def mock_save_incident(inc):
        db_state["incidents"].append(inc)
        return True
        
    def mock_get_incidents():
        return db_state["incidents"]
        
    def mock_get_incident(inc_id):
        return next((i for i in db_state["incidents"] if i.incident_id == inc_id), None)
        
    def mock_update_run_status(run_id, status, expected_statuses=None):
        if run_id in db_state["runs"]:
            if expected_statuses and db_state["runs"][run_id].status not in expected_statuses:
                return False
            db_state["runs"][run_id].status = status
            return True
        return False
        
    def mock_update_run_protection_mode(run_id, mode):
        if run_id in db_state["runs"]:
            db_state["runs"][run_id].protection_mode = mode
            return True
        return False
        
    def mock_get_events(run_id):
        return [e for e in db_state["events"] if e.run_id == run_id]
        
    def mock_save_recovery_action(action):
        return True
        
    def mock_save_plan(plan):
        db_state["plans"][plan.incident_id] = plan
        return True
        
    def mock_save_audit(audit):
        db_state["audits"].append(audit)
        return True
        
    def mock_get_audits(run_id):
        return [a for a in db_state["audits"] if a.run_id == run_id]
        
    import unittest.mock
    
    unittest.mock.patch('cortexheal.runtime.collector.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.runtime.collector.save_run', side_effect=mock_save_run).start()
    unittest.mock.patch('cortexheal.runtime.collector.save_event', side_effect=mock_save_event).start()
    unittest.mock.patch('cortexheal.runtime.collector.save_incident', side_effect=mock_save_incident).start()
    unittest.mock.patch('cortexheal.runtime.collector.get_events_for_run', side_effect=mock_get_events).start()
    unittest.mock.patch('cortexheal.runtime.collector.get_audit_events_for_run', side_effect=mock_get_audits).start()
    unittest.mock.patch('cortexheal.runtime.collector.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.runtime.collector.get_recovery_plan_by_incident', side_effect=lambda i: db_state["plans"].get(i)).start()
    unittest.mock.patch('cortexheal.runtime.collector.save_recovery_plan', side_effect=mock_save_plan).start()
    unittest.mock.patch('cortexheal.adapters.langgraph.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.adapters.langgraph.update_run_status', side_effect=mock_update_run_status).start()
    unittest.mock.patch('cortexheal.adapters.langgraph.update_run_protection_mode', side_effect=mock_update_run_protection_mode).start()
    unittest.mock.patch('cortexheal.adapters.langgraph.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.protection.controller.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.protection.controller.update_run_status', side_effect=mock_update_run_status).start()
    unittest.mock.patch('cortexheal.protection.controller.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.server.api.get_incidents', side_effect=mock_get_incidents).start()
    unittest.mock.patch('cortexheal.server.api.get_incident', side_effect=mock_get_incident).start()
    unittest.mock.patch('cortexheal.server.api.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.recovery.engine.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.recovery.engine.get_events_for_run', side_effect=mock_get_events).start()
    unittest.mock.patch('cortexheal.recovery.executor.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.recovery.executor.get_events_for_run', side_effect=mock_get_events).start()
    unittest.mock.patch('cortexheal.recovery.executor.save_recovery_action', side_effect=mock_save_recovery_action).start()
    unittest.mock.patch('cortexheal.recovery.executor.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.recovery.engine.get_recovery_plan_by_incident', side_effect=lambda i: db_state["plans"].get(i)).start()
    unittest.mock.patch('cortexheal.recovery.engine.save_recovery_plan', side_effect=mock_save_plan).start()
    unittest.mock.patch('cortexheal.recovery.policy.get_audit_events_for_run', side_effect=mock_get_audits).start()
    unittest.mock.patch('cortexheal.server.api.get_recovery_plan_by_incident', side_effect=lambda i: db_state["plans"].get(i)).start()
    unittest.mock.patch('cortexheal.storage.postgres.update_run_status', side_effect=mock_update_run_status).start()
    unittest.mock.patch('cortexheal.storage.postgres.save_recovery_plan', side_effect=mock_save_plan).start()
    unittest.mock.patch('cortexheal.storage.postgres.get_recovery_plan_by_incident', side_effect=lambda i: db_state["plans"].get(i)).start()
    unittest.mock.patch('cortexheal.storage.postgres.get_audit_events_for_run', side_effect=mock_get_audits).start()
    unittest.mock.patch('cortexheal.storage.postgres.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.detection.engine.get_audit_events_for_run', side_effect=mock_get_audits).start()
    unittest.mock.patch('cortexheal.detection.engine.save_audit_event', side_effect=mock_save_audit).start()
    unittest.mock.patch('cortexheal.detection.engine.get_run', side_effect=mock_get_run).start()
    unittest.mock.patch('cortexheal.detection.engine.get_recovery_plan_by_incident', side_effect=lambda i: db_state["plans"].get(i)).start()
    unittest.mock.patch('cortexheal.detection.engine.save_recovery_plan', side_effect=mock_save_plan).start()
    unittest.mock.patch('cortexheal.storage.postgres.get_connection').start()
    
    yield db_state
    
    from cortexheal.runtime.collector import collector
    collector._queue.join()
    unittest.mock.patch.stopall()

def test_full_lifecycle_e2e(mock_db):
    # 1. Developer Setup & Initialization
    adapter = LangGraphAdapter(agent_id="e2e_agent")
    cortex = CortexHeal(adapter=adapter)
    
    # Configure safety threshold lower for test speed
    from cortexheal.runtime.collector import collector
    collector.engine.detectors[0].config.repetition_threshold = 4
    
    builder = StateGraph(AgentState)
    builder.add_node("safety_gate", cortex.safety_gate)
    builder.add_node("agent_node", agent_node)
    builder.set_entry_point("safety_gate")
    builder.add_edge("safety_gate", "agent_node")
    builder.add_conditional_edges("agent_node", should_continue)
    
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    # 2. Agent Starts & hits deterministic Stuck Loop
    run_id = "e2e_run_123"
    config = {"configurable": {"thread_id": run_id}, "callbacks": [cortex.telemetry]}
    
    # Invoke the graph. It should run, loop, get detected, and PAUSE at the safety gate.
    graph.invoke({"input": "start", "count": 0}, config=config)
    
    state = graph.get_state(config)
    
    # 3. Verify Pause
    assert len(state.next) > 0
    assert state.next[0] == "safety_gate"  # Suspended before executing safety_gate node
    assert state.values["count"] >= 4      # Should have looped at least 4 times
    assert state.next[0] == "safety_gate"  # Suspended before executing safety_gate node
    assert state.values["count"] >= 4      # Should have looped at least 4 times
    
    # Let telemetry queue drain
    collector._queue.join()
    
    # 4. Control Plane Interaction
    client = TestClient(app)
    
    # Viewer checks incidents
    response = client.get("/api/incidents", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert response.status_code == 200
    incidents = response.json()["data"]
    
    # Find the incident for our run
    incident = next((i for i in incidents if i["run_id"] == run_id), None)
    assert incident is not None
    assert incident["failure_type"] == "STUCK_LOOP"
    incident_id = incident["incident_id"]
    
    # 5. Recovery Plan Generation
    response = client.get(f"/api/incidents/{incident_id}/plan", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    plan = response.json()
    assert plan["plan_id"] is not None
    print("GENERATED PLAN:", plan)
    
    # 6. Human Approval & Execution (if not auto-executed)
    if plan["status"] == "PROPOSED":
        response = client.post(f"/api/incidents/{incident_id}/plan/approve", headers={"X-API-Key": settings.get_operator_tokens()[0]})
        if response.status_code != 200:
            print("ERROR DETAILS:", response.json())
        assert response.status_code == 200
    else:
        assert plan["status"] == "COMPLETED"
    
    # 7. Resume the agent
    response = client.post(f"/api/runs/{run_id}/resume", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    
    # Continue graph execution (should pass the safety gate now that it's resumed)
    graph.invoke(None, config=config)
    
    state2 = graph.get_state(config)
    assert state2.values["count"] > state.values["count"] # It made progress!
    
    print("E2E Test Passed: Full lifecycle from integration to recovery successfully verified.")


def test_full_lifecycle_unrecoverable_loop_e2e(mock_db):
    # Tests the complete lifecycle for an unrecoverable loop:
    # Observe -> Detect -> Protect (Pause) -> Plan -> Approve & Resume -> Re-execute -> Repeated Failure Detected -> Re-Pause & Verified Repeated Failure
    
    # 1. Developer Setup
    adapter = LangGraphAdapter(agent_id="unrecov_agent")
    cortex = CortexHeal(adapter=adapter)
    
    from cortexheal.runtime.collector import collector
    collector.engine.detectors[0].config.repetition_threshold = 4
    
    builder = StateGraph(AgentState)
    builder.add_node("safety_gate", cortex.safety_gate)
    builder.add_node("agent_node", agent_node)
    builder.set_entry_point("safety_gate")
    builder.add_edge("safety_gate", "agent_node")
    builder.add_conditional_edges("agent_node", should_continue)
    
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    run_id = "e2e_unrecov_456"
    config = {"configurable": {"thread_id": run_id}, "callbacks": [cortex.telemetry]}
    
    # 2. Agent Starts & hits Stuck Loop
    graph.invoke({"input": "start", "count": 0, "run_id": run_id}, config=config)
    state = graph.get_state(config)
    
    # 3. Verify Paused at safety gate
    assert len(state.next) > 0
    assert state.next[0] == "safety_gate"
    assert state.values["count"] >= 4
    collector._queue.join()
    
    # 4. Control Plane: Query Incidents
    client = TestClient(app)
    response = client.get("/api/incidents", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert response.status_code == 200
    incidents = response.json()["data"]
    incident = next((i for i in incidents if i["run_id"] == run_id), None)
    assert incident is not None
    assert incident["failure_type"] == "STUCK_LOOP"
    incident_id = incident["incident_id"]
    
    # 5. Generate and Approve Recovery Plan (if not auto-executed)
    response = client.get(f"/api/incidents/{incident_id}/plan", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    plan = response.json()
    
    if plan["status"] == "PROPOSED":
        response = client.post(f"/api/incidents/{incident_id}/plan/approve", headers={"X-API-Key": settings.get_operator_tokens()[0]})
        assert response.status_code == 200
    else:
        assert plan["status"] == "COMPLETED"
    
    # 6. Resume Run
    response = client.post(f"/api/runs/{run_id}/resume", headers={"X-API-Key": settings.get_operator_tokens()[0]})
    assert response.status_code == 200
    
    # 7. Re-invoke graph. Since agent produces identical failing tool call, it will fail again post-resume.
    graph.invoke(None, config=config)
    collector._queue.join()
    
    # 8. Verify Repeated Failure is Caught and Run is Paused Again
    run = mock_db["runs"].get(run_id)
    assert run.status == "paused"
    
    plan_record = mock_db["plans"].get(incident_id)
    assert plan_record.verification_status == "RECOVERY_REPEATED_FAILURE"
    
    # Check that audit log has RECOVERY_REPEATED_FAILURE
    repeated_audits = [a for a in mock_db["audits"] if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE"]
    assert len(repeated_audits) > 0
    print("Unrecoverable Loop E2E Test Passed: Repeated failure safely re-paused and verified.")

