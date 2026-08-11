import pytest
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from cortexheal.adapters.langgraph import cortexheal_safety_gate
from cortexheal.adapters.langgraph import CortexHealLangGraphCallback
from cortexheal.protection.controller import ProtectionController
from cortexheal.storage.postgres import init_db, get_run, save_run
from cortexheal.models.run import AgentRun
from cortexheal.detection.stuck_loop import Config as SLConfig
from cortexheal.runtime.collector import collector
import uuid

class State(TypedDict):
    count: int

def mock_tool(state: State):
    return {"count": state["count"] + 1}

from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_db():
    with patch('cortexheal.storage.postgres.get_connection') as mock_conn:
        conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = conn
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        # Ensure rowcount > 0 for updates/inserts to be considered successful
        cur.rowcount = 1 
        cur.fetchone.return_value = {
            "run_id": "test", "agent_id": "test", "framework": "langgraph", "status": "running"
        }
        cur.fetchall.return_value = []
        yield conn

@pytest.fixture(autouse=True)
def setup_env():
    # Configure low threshold for fast testing
    config = SLConfig()
    config.repetition_threshold = 3
    collector.engine.detectors[0].config = config

def test_actual_graph_pause_and_resume():
    # 1. Build the graph with safety gate
    builder = StateGraph(State)
    builder.add_node("safety_gate", cortexheal_safety_gate)
    builder.add_node("mock_tool", mock_tool)
    
    # Simple loop A -> B -> A until interrupted or done
    builder.set_entry_point("safety_gate")
    builder.add_edge("safety_gate", "mock_tool")
    
    # We will simulate a loop by manually adding edge back, but to avoid infinite loops in test 
    # if protection fails, we use a conditional edge
    def should_continue(state):
        if state["count"] > 10:
            return END
        return "safety_gate"
        
    builder.add_conditional_edges("mock_tool", should_continue)
    
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    run_id = str(uuid.uuid4())
    # Pre-save run since SDK relies on it
    save_run(AgentRun(framework="langgraph", run_id=run_id, agent_id="test_agent", status="running"))
    
    cb = CortexHealLangGraphCallback(agent_id="test_agent", run_id=run_id)
    config = {"configurable": {"thread_id": run_id}, "callbacks": [cb]}
    
    # 2. Invoke the graph
    # We use a mocked run to let the safety gate pass initially, then pause later
    with patch('cortexheal.adapters.langgraph.get_run') as mock_sg_get_run:
        # First call to safety gate returns running, second call returns pause_requested
        mock_sg_get_run.side_effect = [
            AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running"),
            AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running"),
            AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running"),
            AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="pause_requested")
        ]
        
        with patch('cortexheal.protection.controller.get_run', return_value=AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running")):
            graph.invoke({"count": 0}, config=config)
    
    # 3. Verify it paused
    state = graph.get_state(config)
    assert len(state.next) > 0
    assert state.next[0] == "safety_gate" # It is suspended AT the safety gate
    assert state.values["count"] >= 3
    
    db_run = AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="paused")
    with patch('cortexheal.protection.controller.get_run', return_value=db_run), \
         patch('cortexheal.adapters.langgraph.get_run', return_value=db_run):
        
        # 4. Resume
        controller = ProtectionController()
        controller.resume(run_id, actor_id="test_user")
        
        # Manually update our mock db_run object to simulate the DB change
        db_run.status = "resume_requested"
        
        # 5. Invoke to continue
        graph.invoke(None, config=config)
        
        state3 = graph.get_state(config)
        # It resumed, ran, and might have hit the pause again!
        assert state3.values["count"] > state.values["count"]
        
    print("Test passed: Real graph pause and resume validated.")
