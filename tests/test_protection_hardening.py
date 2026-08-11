import pytest
import time
import uuid
from typing import TypedDict
from unittest.mock import patch, MagicMock

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from cortexheal.adapters.langgraph import cortexheal_safety_gate
from cortexheal.adapters.langgraph import CortexHealLangGraphCallback
from cortexheal.protection.controller import ProtectionController
from cortexheal.storage.postgres import init_db, get_run, save_run
from cortexheal.models.run import AgentRun
from cortexheal.detection.stuck_loop import Config as SLConfig
from cortexheal.runtime.collector import collector

class State(TypedDict):
    count: int
    executed_nodes: list

def tool_a(state: State):
    state["executed_nodes"].append("tool_a")
    return {"count": state["count"] + 1, "executed_nodes": state["executed_nodes"]}

def tool_b(state: State):
    state["executed_nodes"].append("tool_b")
    return {"count": state["count"] + 1, "executed_nodes": state["executed_nodes"]}

@pytest.fixture(autouse=True)
def mock_db():
    with patch('cortexheal.storage.postgres.get_connection') as mock_conn:
        conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = conn
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        cur.rowcount = 1 
        cur.fetchone.return_value = {
            "run_id": "test", "agent_id": "test", "framework": "langgraph", "status": "running"
        }
        cur.fetchall.return_value = []
        yield conn

@pytest.fixture(autouse=True)
def setup_env():
    config = SLConfig()
    config.repetition_threshold = 3
    collector.engine.detectors[0].config = config

def test_timing_and_execution_order():
    builder = StateGraph(State)
    builder.add_node("safety_gate", cortexheal_safety_gate)
    builder.add_node("tool_a", tool_a)
    builder.add_node("tool_b", tool_b)
    
    # We want tool_a -> tool_a -> tool_a (threshold) -> safety_gate (interrupts) -> tool_b
    builder.set_entry_point("safety_gate")
    
    def route(state):
        if state["count"] < 3:
            return "tool_a"
        elif state["count"] == 3:
            return "tool_b"
        return END
        
    builder.add_conditional_edges("safety_gate", route)
    builder.add_edge("tool_a", "safety_gate")
    builder.add_edge("tool_b", END)
    
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    run_id = str(uuid.uuid4())
    save_run(AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running", protection_mode="DISABLED"))
    
    cb = CortexHealLangGraphCallback(agent_id="test", run_id=run_id)
    config = {"configurable": {"thread_id": run_id}, "callbacks": [cb]}
    
    # Track timings
    timings = {}
    
    # 1. First run, hits safety_gate and tool_a 3 times. 
    # At count=3, tool_a is done. Next is safety_gate, but wait! We need the detector to fire!
    # Our mocked DB doesn't actually trigger incidents because we don't mock it to run the callback logic perfectly here without real DB.
    # Wait, the callback DOES execute engine.evaluate() even with a mocked DB!
    
    # Actually, we will just manually mock the run state to 'pause_requested' at count=3 to simulate the exact boundary.
    with patch('cortexheal.adapters.langgraph.get_run') as mock_sg_get_run:
        call_count = [0]
        def side_effect_sg(r_id):
            call_count[0] += 1
            # 1st call: count=0, routes to tool_a
            # 2nd call: count=1, routes to tool_a
            # 3rd call: count=2, routes to tool_a
            # 4th call: count=3 (threshold reached), this should pause
            if call_count[0] >= 4:
                timings["pause_request_time"] = time.time()
                return AgentRun(framework="langgraph", run_id=r_id, agent_id="test", status="pause_requested", protection_mode="ACTIVE")
            return AgentRun(framework="langgraph", run_id=r_id, agent_id="test", status="running", protection_mode="ACTIVE")
            
        mock_sg_get_run.side_effect = side_effect_sg
        
        timings["start_time"] = time.time()
        graph.invoke({"count": 0, "executed_nodes": []}, config=config)
        timings["actual_interrupt_time"] = time.time()
        
    state = graph.get_state(config)
    
    # PROVE NO NEXT NODE EXECUTED
    # executed_nodes should exactly be ['tool_a', 'tool_a', 'tool_a']
    assert state.values["executed_nodes"] == ['tool_a', 'tool_a', 'tool_a']
    assert "tool_b" not in state.values["executed_nodes"]
    
    assert len(state.next) == 1
    assert state.next[0] == "safety_gate"
    
    print(f"Start -> Interrupt latency: {(timings['actual_interrupt_time'] - timings['start_time'])*1000:.2f}ms")
    
    # Resume
    with patch('cortexheal.protection.controller.get_run', return_value=AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="paused", protection_mode="ACTIVE")):
        controller = ProtectionController()
        controller.resume(run_id, actor_id="test_user")
        
    with patch('cortexheal.adapters.langgraph.get_run', return_value=AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="resume_requested", protection_mode="ACTIVE")):
        graph.invoke(None, config=config)
        
    state_after = graph.get_state(config)
    # PROVE TOOL_B EXECUTED EXACTLY ONCE AFTER RESUME
    assert state_after.values["executed_nodes"] == ['tool_a', 'tool_a', 'tool_a', 'tool_b']
    assert len(state_after.next) == 0

def test_missing_safety_gate():
    # If the user graph has no safety gate, protection stays DISABLED
    controller = ProtectionController()
    run_id = str(uuid.uuid4())
    
    run = AgentRun(framework="langgraph", run_id=run_id, agent_id="test", status="running", protection_mode="DISABLED")
    with patch('cortexheal.protection.controller.get_run', return_value=run):
        # Attempt to pause
        controller.request_pause(run_id, "inc_1", "test")
        
        # It should log a warning and NOT update status
        assert run.status == "running" # State remains unaffected

def test_degraded_state_on_db_failure():
    controller = ProtectionController()
    run_id = str(uuid.uuid4())
    
    with patch('cortexheal.protection.controller.get_run', side_effect=Exception("DB Connection Lost")):
        controller.request_pause(run_id, "inc_1", "test")
        # Should not crash (fail open) but log DEGRADED
        # The run status remains unaffected (we can't update it)
