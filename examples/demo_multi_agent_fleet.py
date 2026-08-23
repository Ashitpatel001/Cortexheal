"""
CortexHeal Demo: Multi-Agent Enterprise Fleet Simulation
--------------------------------------------------------
Simulates 5 distinct enterprise agent workloads running in parallel across
LangGraph, AutoGen, and CrewAI frameworks, generating realistic mix of healthy
runs, deterministic safety interventions, and budget guardrails.
"""

import time
import uuid
from typing import Dict, Any

from cortexheal.runtime.collector import RuntimeCollector
from cortexheal.models.events import RuntimeEvent, TokenUsage
from cortexheal.storage.postgres import get_run, get_incidents, init_db

AGENTS = [
    {
        "agent_id": "support-ticket-router",
        "framework": "langgraph",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "behavior": "HEALTHY",
        "steps": 6,
        "cost_per_step": 0.015,
        "tokens_per_step": 850
    },
    {
        "agent_id": "sql-analyst-agent",
        "framework": "autogen",
        "model": "claude-3-5-sonnet",
        "provider": "anthropic",
        "behavior": "STUCK_LOOP",
        "steps": 5,
        "cost_per_step": 0.04,
        "tokens_per_step": 1800
    },
    {
        "agent_id": "document-summarizer-prod",
        "framework": "langgraph",
        "model": "gpt-4o",
        "provider": "openai",
        "behavior": "BUDGET_OVERRUN",
        "steps": 4,
        "cost_per_step": 0.35,
        "tokens_per_step": 16000
    },
    {
        "agent_id": "code-reviewer-bot",
        "framework": "crewai",
        "model": "gemini-1.5-pro",
        "provider": "google",
        "behavior": "HEALTHY",
        "steps": 8,
        "cost_per_step": 0.02,
        "tokens_per_step": 1200
    },
    {
        "agent_id": "billing-reconciliation-worker",
        "framework": "langgraph",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "behavior": "STUCK_LOOP",
        "steps": 5,
        "cost_per_step": 0.01,
        "tokens_per_step": 600
    }
]

def simulate_agent(collector: RuntimeCollector, spec: Dict[str, Any]):
    run_id = f"fleet_{spec['agent_id'][:10]}_{uuid.uuid4().hex[:6]}"
    print(f"[*] Launching agent: {spec['agent_id']} ({spec['framework'].upper()}, {spec['model']}) -> Run: {run_id}")

    # 1. Start event
    collector.ingest_event(RuntimeEvent(
        run_id=run_id,
        agent_id=spec["agent_id"],
        framework=spec["framework"],
        event_type="RUN_STARTED",
        sequence_number=0,
        idempotency_key=f"{run_id}_start",
        status="pending",
        model=spec["model"],
        provider=spec["provider"]
    ))

    # 2. Ingest tool execution events based on behavior
    for step in range(1, spec["steps"] + 1):
        if spec["behavior"] == "STUCK_LOOP":
            # Repetitive identical hashes
            args_hash = "fixed_query_hash_stuck"
            resp_hash = "fixed_empty_result_hash"
            tool_name = "query_database_table"
        elif spec["behavior"] == "BUDGET_OVERRUN":
            args_hash = f"arg_doc_chunk_{step}"
            resp_hash = f"resp_doc_chunk_{step}"
            tool_name = "large_context_extraction"
        else: # HEALTHY
            args_hash = f"arg_healthy_task_{step}_{uuid.uuid4().hex[:4]}"
            resp_hash = f"resp_healthy_result_{step}_{uuid.uuid4().hex[:4]}"
            tool_name = "execute_workflow_step"

        event = RuntimeEvent(
            run_id=run_id,
            agent_id=spec["agent_id"],
            framework=spec["framework"],
            event_type="TOOL_CALL_COMPLETED",
            sequence_number=step,
            idempotency_key=f"{run_id}_step_{step}",
            status="success",
            tool=tool_name,
            arguments_hash=args_hash,
            response_hash=resp_hash,
            tokens=TokenUsage(
                prompt=int(spec["tokens_per_step"] * 0.7),
                completion=int(spec["tokens_per_step"] * 0.3),
                total=spec["tokens_per_step"]
            ),
            cost=spec["cost_per_step"],
            model=spec["model"],
            provider=spec["provider"]
        )
        collector.ingest_event(event)
        time.sleep(0.01)

    return run_id

def main():
    print("=" * 75)
    print("  CORTEXHEAL MULTI-AGENT ENTERPRISE FLEET SIMULATION")
    print("=" * 75)

    init_db()
    collector = RuntimeCollector()

    run_ids = []
    for spec in AGENTS:
        rid = simulate_agent(collector, spec)
        run_ids.append(rid)

    collector._queue.join()
    time.sleep(0.5)

    print("\n" + "=" * 75)
    print("  FLEET STATUS SUMMARY")
    print("=" * 75)
    
    for rid in run_ids:
        run = get_run(rid)
        incidents = [i for i in get_incidents() if i.run_id == rid]
        inc_str = f"INCIDENT: {incidents[0].failure_type} ({incidents[0].severity})" if incidents else "HEALTHY - NOMINAL"
        print(f"Run: {rid:<30} | Agent: {run.agent_id:<30} | Status: {run.status.upper():<10} | {inc_str}")

if __name__ == "__main__":
    main()
