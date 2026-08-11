import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END

from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.runtime.collector import collector

class AgentState(TypedDict):
    count: int

def dummy_tool_node(state: AgentState):
    print(f"Executing healthy tool...")
    time.sleep(0.1)
    return {"count": state.get("count", 0) + 1}

def should_continue(state: AgentState):
    if state["count"] >= 3:
        return END
    return "tool_node"

run_id = str(uuid.uuid4())
print(f"Starting HEALTHY agent run: {run_id}")

adapter = LangGraphAdapter(agent_id="healthy_agent")
cortex = CortexHeal(adapter=adapter)

builder = StateGraph(AgentState)
builder.add_node("safety_gate", cortex.safety_gate)
builder.add_node("tool_node", dummy_tool_node)

builder.set_entry_point("safety_gate")
builder.add_edge("safety_gate", "tool_node")
builder.add_conditional_edges("tool_node", should_continue)

graph = builder.compile()

config = {"configurable": {"thread_id": run_id}, "callbacks": [cortex.telemetry]}
graph.invoke({"count": 0}, config=config)

print("Waiting for telemetry queue to drain...")
collector._queue.join()
print(f"Execution complete. Run ID: {run_id}")

# Verification
from cortexheal.storage.postgres import get_events_for_run, get_audit_events_for_run
events = get_events_for_run(run_id)
audits = get_audit_events_for_run(run_id)

print(f"Events: {[e.event_type for e in events]}")
print(f"Audits: {[a.action for a in audits]}")
