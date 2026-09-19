import pytest
from cortexheal.storage.postgres import get_run, get_recovery_plan_by_incident, get_audit_events_for_run
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
    
    collector._queue.join()
    time.sleep(0.1)
    return {"count": state["count"] + 1, "run_id": current_run_id}

def should_continue(state: AgentState):
    if state["count"] > 10:
        return END
    return "safety_gate"

@pytest.fixture(autouse=True)
def clean_db():
    from cortexheal.storage.postgres import init_db, get_connection
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE audit_events, recovery_plans, notification_records, webhook_configs, incidents, events, runs, api_keys CASCADE")
            conn.commit()
    from cortexheal.runtime.collector import collector
    collector.engine._emitted.clear()
    
    yield
    
    collector._queue.join()
def test_full_lifecycle_e2e(clean_db):
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
    assert state.values["count"] >= 3      # Should have looped at least 4 times
    assert state.next[0] == "safety_gate"  # Suspended before executing safety_gate node
    assert state.values["count"] >= 3      # Should have looped at least 4 times
    
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


def test_full_lifecycle_unrecoverable_loop_e2e(clean_db):
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
    assert state.values["count"] >= 3
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
    run = get_run(run_id)
    assert run.status == "paused"
    
    plan_record = get_recovery_plan_by_incident(incident_id)
    assert plan_record.verification_status == "RECOVERY_REPEATED_FAILURE"
    
    # Check that audit log has RECOVERY_REPEATED_FAILURE
    repeated_audits = [a for a in get_audit_events_for_run(run_id) if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE"]
    assert len(repeated_audits) > 0
    print("Unrecoverable Loop E2E Test Passed: Repeated failure safely re-paused and verified.")





