import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.runtime.collector import collector
from cortexheal.models.events import RuntimeEvent

MAX_ITERATIONS = 20

class AgentState(TypedDict):
    count: int
    output: str

run_id = str(uuid.uuid4())

def dummy_tool_node(state: AgentState):
    count = state.get("count", 0)
    
    if count >= MAX_ITERATIONS:
        print(f"Agent reached MAX_ITERATIONS ({MAX_ITERATIONS}). Exiting safely.")
        return {"count": count, "output": "Done"}
        
    print(f"Executing deterministic failing tool (Iteration {count})")
        
    # UNRECOVERABLE: Even if resumed, it does the exact same failing thing!
    event = RuntimeEvent(
        run_id=run_id,
        agent_id="unrecoverable_agent",
        framework="langgraph",
        event_type="TOOL_CALL_COMPLETED",
        sequence_number=count,
        idempotency_key=f"{run_id}_tool_{count}",
        status="success",
        tool="search_database",
        arguments_hash="hash_same_args",
        response_hash="hash_same_resp"
    )
    
    collector.ingest_event(event)
    time.sleep(0.05)
    
    return {"count": count + 1, "output": "Repeating..."}

def should_continue(state: AgentState):
    if state["count"] >= MAX_ITERATIONS:
        return END
    return "safety_gate"

# 1. Setup CortexHeal
adapter = LangGraphAdapter(agent_id="unrecoverable_agent")
cortex = CortexHeal(adapter=adapter)

# Lower threshold for fast testing
collector.engine.detectors[0].config.repetition_threshold = 4

# 2. Build Graph
builder = StateGraph(AgentState)
builder.add_node("safety_gate", cortex.safety_gate)
builder.add_node("tool_node", dummy_tool_node)

builder.set_entry_point("safety_gate")
builder.add_edge("safety_gate", "tool_node")
builder.add_conditional_edges("tool_node", should_continue)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# 3. Execute Graph
print(f"Starting UNRECOVERABLE agent run: {run_id}")
config = {"configurable": {"thread_id": run_id}, "callbacks": [cortex.telemetry]}

try:
    graph.invoke({"count": 0, "output": ""}, config=config)
except Exception as e:
    print(f"Execution interrupted: {e}")

# Wait for collector to create incident
collector._queue.join()
import time
time.sleep(0.5)


# Simulate Operator Approval of Recovery Plan
import urllib.request, json

req = urllib.request.Request('http://127.0.0.1:8000/api/incidents')
req.add_header('X-API-Key', 'dev-admin-key')
try:
    resp = urllib.request.urlopen(req)
    incidents = json.loads(resp.read())['data']
    inc = [i for i in incidents if i['run_id'] == run_id]
    if inc:
        incident_id = inc[0]['incident_id']
        print(f"Approving recovery for incident {incident_id}...")
        
        # 1. Generate plan so that it exists in the DB
        req2 = urllib.request.Request(f'http://127.0.0.1:8000/api/incidents/{incident_id}/plan')
        req2.add_header('X-API-Key', 'dev-admin-key')
        urllib.request.urlopen(req2)
        
        # 2. Execute plan so outcome is recorded
        req3 = urllib.request.Request(f"http://127.0.0.1:8000/api/incidents/{incident_id}/plan/approve", method="POST")
        req3.add_header("X-API-Key", "dev-admin-key")
        try:
            urllib.request.urlopen(req3)
            print("Plan Executed via API.")
        except urllib.error.HTTPError as e:
            print(f"Failed to execute plan: {e.read()}")
        
        # Call the direct resume API
        print(f"Resuming run {run_id} directly...")
        req4 = urllib.request.Request(f'http://127.0.0.1:8000/api/runs/{run_id}/resume', method='POST')
        req4.add_header('X-API-Key', 'dev-admin-key')
        urllib.request.urlopen(req4)
        print("Run resumed via API! Re-invoking graph...")
        
        # Re-invoke after resume
        try:
            graph.invoke(None, config=config)
        except Exception as e:
            print(f"Execution interrupted again: {e}")
except Exception as e:
    print("API Error:", e)

# Wait for telemetry to flush
print("Waiting for telemetry queue to drain...")
collector._queue.join()
print(f"Execution complete. Run ID: {run_id}")
