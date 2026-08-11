import pytest
import time
from cortexheal.models.events import RuntimeEvent
from cortexheal.detection.engine import DetectionEngine
from cortexheal.detection.stuck_loop import Config as SLConfig
from cortexheal.detection.budget import BudgetConfig

def make_event(event_type, tool=None, args_hash=None, resp_hash=None, cost=None, run_id="run_1"):
    return RuntimeEvent(framework="langgraph", 
        run_id=run_id,
        agent_id="agent_1",
        event_type=event_type,
        status="success",
        sequence_number=1,
        idempotency_key=f"idem_{time.time()}_{hash(tool)}",
        tool=tool,
        arguments_hash=args_hash,
        response_hash=resp_hash,
        cost=cost
    )

def test_A_healthy_agent():
    engine = DetectionEngine()
    events = [
        make_event("TOOL_CALL_COMPLETED", "tool_a", "args_1", "resp_1"),
        make_event("TOOL_CALL_COMPLETED", "tool_b", "args_2", "resp_2"),
        make_event("TOOL_CALL_COMPLETED", "tool_a", "args_3", "resp_3")
    ]
    # Evaluate sequentially as if in stream
    incidents = []
    for e in events:
        incidents.extend(engine.evaluate(e))
    assert len(incidents) == 0

def test_B_exact_stuck_loop():
    config = SLConfig()
    config.repetition_threshold = 3
    engine = DetectionEngine(sl_config=config)
    
    events = [
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r")
    ]
    
    incidents = []
    for e in events:
        incidents.extend(engine.evaluate(e))
        
    assert len(incidents) == 1
    assert incidents[0].failure_type == "STUCK_LOOP"
    assert incidents[0].evidence['repetitions'] == 3

def test_C_legitimate_repeated_tool():
    config = SLConfig()
    config.repetition_threshold = 3
    config.ignored_tools = ["poll_status"]
    engine = DetectionEngine(sl_config=config)
    
    events = [
        make_event("TOOL_CALL_COMPLETED", "poll_status", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "poll_status", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "poll_status", "hash_a", "hash_r")
    ]
    
    incidents = []
    for e in events:
        incidents.extend(engine.evaluate(e))
        
    assert len(incidents) == 0

def test_D_budget_exceeded():
    config = BudgetConfig()
    config.max_cost_usd = 1.00
    engine = DetectionEngine(budget_config=config)
    
    events = [
        make_event("LLM_CALL_COMPLETED", cost=0.50),
        make_event("LLM_CALL_COMPLETED", cost=0.40),
        make_event("LLM_CALL_COMPLETED", cost=0.20)
    ]
    
    incidents = []
    for e in events:
        incidents.extend(engine.evaluate(e))
        
    assert len(incidents) == 1
    assert incidents[0].failure_type == "BUDGET_EXCEEDED"
    assert incidents[0].observed_value == 1.10

def test_E_different_runs():
    config = SLConfig()
    config.repetition_threshold = 2
    engine = DetectionEngine(sl_config=config)
    
    e1 = make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r", run_id="run_1")
    e2 = make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r", run_id="run_1")
    
    e3 = make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r", run_id="run_2")
    e4 = make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r", run_id="run_2")
    
    i1 = engine.evaluate(e1)
    i1.extend(engine.evaluate(e2))
    i2 = engine.evaluate(e3)
    i2.extend(engine.evaluate(e4))
    
    assert len(i1) == 1
    assert len(i2) == 1
    assert i1[0].run_id == "run_1"
    assert i2[0].run_id == "run_2"

def test_F_recovery_after_repetition():
    config = SLConfig()
    config.repetition_threshold = 3
    engine = DetectionEngine(sl_config=config)
    
    events = [
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r"),
        make_event("TOOL_CALL_COMPLETED", "tool_b", "hash_b", "hash_r2"), # Recovery
        make_event("TOOL_CALL_COMPLETED", "tool_a", "hash_a", "hash_r")
    ]
    
    incidents = []
    for e in events:
        incidents.extend(engine.evaluate(e))
        
    assert len(incidents) == 0 # Sequence was broken before hitting 3

def test_H_1000_repetitions_one_incident():
    config = SLConfig()
    config.repetition_threshold = 8
    engine = DetectionEngine(sl_config=config)
    
    incidents = []
    for i in range(1000):
        event = make_event("TOOL_CALL_COMPLETED", "tool_x", "hash_x", "hash_r")
        incidents.extend(engine.evaluate(event))
        
    # We expect exactly ONE incident thanks to engine-level deduplication
    assert len(incidents) == 1
    assert incidents[0].failure_type == "STUCK_LOOP"
    assert incidents[0].evidence['repetitions'] == 8
