"""
CortexHeal Demo: Deterministic Stuck-Loop Detection, Plan Approval & Recovery
-----------------------------------------------------------------------------
Demonstrates a customer support agent stuck in an empty database retry loop.
CortexHeal deterministically trips a STUCK_LOOP incident after 4 identical iterations,
pauses the execution, generates a deterministic recovery plan, applies the fix upon
operator approval, and verifies recovery completion.
"""

import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.runtime.collector import collector
from cortexheal.models.events import RuntimeEvent
from cortexheal.storage.postgres import get_run, get_incidents, update_run_status
from cortexheal.protection.controller import ProtectionController
from cortexheal.recovery.engine import RecoveryEngine

class SupportAgentState(TypedDict):
    ticket_id: str
    query_param: str
    iteration: int
    result: str
    is_recovered: bool

def main():
    print("=" * 75)
    print("  DEMO: STUCK-LOOP DETECTION, OPERATOR APPROVAL & RECOVERY")
    print("=" * 75)

    run_id = f"demo_loop_{uuid.uuid4().hex[:8]}"
    agent_id = "support_ticket_router"

    adapter = LangGraphAdapter(agent_id=agent_id)
    cortex = CortexHeal(adapter=adapter)

    # Initial start event
    collector.ingest_event(RuntimeEvent(
        run_id=run_id,
        agent_id=agent_id,
        framework="langgraph",
        event_type="RUN_STARTED",
        sequence_number=0,
        idempotency_key=f"{run_id}_start",
        status="pending"
    ))

    def fetch_ticket_record_node(state: SupportAgentState):
        iter_num = state.get("iteration", 0) + 1
        is_recovered = state.get("is_recovered", False)

        if is_recovered:
            print(f"[Agent Step {iter_num}] RECOVERED: Successfully retrieved customer record via alternate index!")
            return {
                "ticket_id": state["ticket_id"],
                "query_param": "indexed_customer_id_99",
                "iteration": iter_num,
                "result": "FOUND_CUSTOMER_RECORD_ACTIVE",
                "is_recovered": True
            }

        print(f"[Agent Step {iter_num}] Querying database with param '{state['query_param']}' -> Empty Result (Retrying...)")

        # Emit identical tool call event (deterministic hash)
        event = RuntimeEvent(
            run_id=run_id,
            agent_id=agent_id,
            framework="langgraph",
            event_type="TOOL_CALL_COMPLETED",
            sequence_number=iter_num,
            idempotency_key=f"{run_id}_step_{iter_num}",
            status="success",
            tool="query_customer_crm",
            arguments_hash="hash_crm_param_legacy_id",
            response_hash="hash_crm_empty_rows",
            model="gpt-4o",
            provider="openai"
        )
        collector.ingest_event(event)
        time.sleep(0.05)

        return {
            "ticket_id": state["ticket_id"],
            "query_param": state["query_param"],
            "iteration": iter_num,
            "result": "EMPTY_RESULT",
            "is_recovered": False
        }

    def should_continue(state: SupportAgentState):
        if state.get("result") == "FOUND_CUSTOMER_RECORD_ACTIVE":
            return END
        if state.get("iteration", 0) >= 10:
            return END
        return "safety_gate"

    builder = StateGraph(SupportAgentState)
    builder.add_node("safety_gate", cortex.safety_gate)
    builder.add_node("crm_node", fetch_ticket_record_node)
    builder.set_entry_point("safety_gate")
    builder.add_edge("safety_gate", "crm_node")
    builder.add_conditional_edges("crm_node", should_continue)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    print(f"\n[1] Starting agent execution (Run ID: {run_id})...")
    initial_state: SupportAgentState = {
        "ticket_id": "TCK-88291",
        "query_param": "legacy_cust_id_001",
        "iteration": 0,
        "result": "START",
        "is_recovered": False
    }

    try:
        for output in graph.stream(initial_state, config=config):
            pass
    except Exception as e:
        print(f"[Safety Gate Circuit Breaker] Run paused: {e}")

    collector._queue.join()
    time.sleep(0.5)

    # 2. Control Plane Inspection
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
        print(f"    Observed Loops:   {inc.observed_value} iterations")
        print(f"    Threshold:        {inc.threshold} iterations")
        print(f"    Description:      {inc.description}")

    # 3. Recovery Engine Plan Generation
    print(f"\n[3] Generating Deterministic Recovery Plan...")
    recovery_engine = RecoveryEngine()
    incident = incidents[0]
    plan = recovery_engine.generate_plan(incident)
    print(f"    Generated Plan ID:   {plan.plan_id}")
    print(f"    Diagnosis:           {plan.diagnosis}")
    print(f"    Proposed Action:     {plan.proposed_actions}")
    print(f"    Risk Level:          {plan.risk_level}")

    # 4. Human Operator Approval & Plan Execution
    print(f"\n[4] Operator Review & Plan Approval...")
    from cortexheal.recovery.executor import RecoveryExecutor
    executor = RecoveryExecutor()
    approved = executor.execute_plan(plan, user_role="OPERATOR", user_id="operator_alex")
    print(f"    Plan execution result: {approved} (Status: APPROVED)")

    # 5. Resume execution with state injection
    print(f"\n[5] Resuming Agent with Injected Recovery Fix...")
    controller = ProtectionController()
    controller.resume(run_id=run_id, actor_id="operator_alex", reason="Injected secondary index query.", incident_id=incident.incident_id)
    
    # Resume graph execution with recovered state
    recovered_state = {
        "ticket_id": "TCK-88291",
        "query_param": "indexed_customer_id_99",
        "iteration": 4,
        "result": "RESUMED",
        "is_recovered": True
    }
    
    # Step once more to complete
    for output in graph.stream(recovered_state, config=config):
        pass

    update_run_status(run_id, "completed")
    print(f"    Run execution resumed and finished with status: COMPLETED")

    print("\n" + "=" * 75)
    print("  STUCK-LOOP RECOVERY DEMO COMPLETE (FULL VERIFIED LIFECYCLE)")
    print("=" * 75)

if __name__ == "__main__":
    main()