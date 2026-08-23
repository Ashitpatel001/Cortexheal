"""
CortexHeal Demo: Deterministic Budget Overrun Protection & Recovery
-------------------------------------------------------------------
Demonstrates an agent burning token budget on repetitive LLM / web search calls.
CortexHeal deterministically detects the cumulative budget breach ($1.00 threshold),
pauses the run, generates a recovery diagnosis, and resumes upon operator authorization.
"""

import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.runtime.collector import collector
from cortexheal.models.events import RuntimeEvent, TokenUsage
from cortexheal.storage.postgres import get_run, get_incidents, update_run_status
from cortexheal.protection.controller import ProtectionController

class BudgetAgentState(TypedDict):
    query: str
    iteration: int
    total_tokens: int
    status: str

def main():
    print("=" * 75)
    print("  DEMO: BUDGET OVERRUN DETECTION & RECOVERY LIFECYCLE")
    print("=" * 75)

    run_id = f"demo_budget_{uuid.uuid4().hex[:8]}"
    agent_id = "document_summarizer_prod"
    budget_threshold = 1.00  # $1.00 limit

    adapter = LangGraphAdapter(agent_id=agent_id)
    cortex = CortexHeal(adapter=adapter)

    # Initial run event
    collector.ingest_event(RuntimeEvent(
        run_id=run_id,
        agent_id=agent_id,
        framework="langgraph",
        event_type="RUN_STARTED",
        sequence_number=0,
        idempotency_key=f"{run_id}_start",
        status="pending",
        model="gpt-4o",
        provider="openai"
    ))

    def llm_query_node(state: BudgetAgentState):
        iter_num = state.get("iteration", 0) + 1
        current_tokens = state.get("total_tokens", 0)
        
        # Each iteration consumes 15,000 prompt tokens and 5,000 completion tokens (~$0.35 per call)
        iter_prompt_tokens = 15000
        iter_comp_tokens = 5000
        iter_total = iter_prompt_tokens + iter_comp_tokens
        iter_cost = 0.35

        print(f"[Agent Step {iter_num}] Executing heavy LLM synthesis ({iter_total:,} tokens, +${iter_cost:.2f})...")

        event = RuntimeEvent(
            run_id=run_id,
            agent_id=agent_id,
            framework="langgraph",
            event_type="TOOL_CALL_COMPLETED",
            sequence_number=iter_num,
            idempotency_key=f"{run_id}_step_{iter_num}",
            status="success",
            tool="synthesize_large_document",
            arguments_hash=f"arg_hash_doc_{iter_num}",
            response_hash=f"resp_hash_summary_{iter_num}",
            tokens=TokenUsage(
                prompt=iter_prompt_tokens,
                completion=iter_comp_tokens,
                total=iter_total
            ),
            cost=iter_cost,
            model="gpt-4o",
            provider="openai"
        )
        collector.ingest_event(event)
        time.sleep(0.05)

        return {
            "query": state["query"],
            "iteration": iter_num,
            "total_tokens": current_tokens + iter_total,
            "status": "in_progress"
        }

    def should_continue(state: BudgetAgentState):
        if state.get("iteration", 0) >= 5:
            return END
        return "safety_gate"

    builder = StateGraph(BudgetAgentState)
    builder.add_node("safety_gate", cortex.safety_gate)
    builder.add_node("llm_node", llm_query_node)
    builder.set_entry_point("safety_gate")
    builder.add_edge("safety_gate", "llm_node")
    builder.add_conditional_edges("llm_node", should_continue)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    print(f"\n[1] Starting agent execution (Run ID: {run_id})...")
    initial_state: BudgetAgentState = {
        "query": "Synthesize 100-page financial quarterly reports",
        "iteration": 0,
        "total_tokens": 0,
        "status": "started"
    }

    try:
        for output in graph.stream(initial_state, config=config):
            pass
    except Exception as e:
        print(f"[Safety Gate Triggered] Execution paused by CortexHeal: {e}")

    collector._queue.join()
    time.sleep(0.5)

    # 2. Check Run Status and Incident
    run = get_run(run_id)
    incidents = [i for i in get_incidents() if i.run_id == run_id]
    print(f"\n[2] Control Plane Inspection:")
    print(f"    Run Status:       {run.status.upper()}")
    print(f"    Protection Mode:  {run.protection_mode}")
    print(f"    Incidents Found:  {len(incidents)}")
    if incidents:
        inc = incidents[0]
        print(f"    Failure Type:     {inc.failure_type}")
        print(f"    Severity:         {inc.severity}")
        print(f"    Observed Cost:    ${inc.observed_value}")
        print(f"    Budget Limit:     ${inc.threshold}")
        print(f"    Description:      {inc.description}")

    # 3. Simulate Operator Review and Resumption
    print(f"\n[3] Operator Action: Approving budget increase & resuming run...")
    controller = ProtectionController()
    controller.resume(run_id=run_id, actor_id="operator_sarah", reason="Authorized $5.00 budget expansion for high-priority executive summary.", incident_id=incidents[0].incident_id if incidents else None)
    
    # Complete run status transition
    update_run_status(run_id, "completed")
    print(f"    Run successfully resumed and transitioned to COMPLETED.")

    print("\n" + "=" * 75)
    print("  BUDGET OVERRUN DEMO COMPLETE (DETERMINISTIC ZERO-LLM SAFETY)")
    print("=" * 75)

if __name__ == "__main__":
    main()
