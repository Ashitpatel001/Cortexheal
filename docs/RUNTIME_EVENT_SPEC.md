# Normalized Runtime Event Specification

The canonical runtime event model bridges the gap between various AI frameworks (e.g., LangGraph) and the CortexHeal Runtime Engine.

## Schema

```json
{
  "event_id": "uuid",
  "run_id": "uuid",
  "agent_id": "string",
  "parent_run_id": "uuid | null",
  "timestamp": "iso8601",
  "event_type": "string (e.g., 'tool_call', 'tool_result', 'state_update', 'error')",
  
  // Tool specific
  "tool": "string | null",
  "arguments_hash": "string | null",
  "response_hash": "string | null",
  
  // Cost tracking
  "tokens": {
    "prompt": "int",
    "completion": "int",
    "total": "int"
  },
  "cost": "float (USD)",
  
  // Performance & State
  "latency_ms": "int",
  "state_hash": "string",
  "status": "string (e.g., 'pending', 'success', 'failed')",
  
  // Metadata (Optional/Contextual)
  "sequence_number": "int",
  "framework": "string (e.g., 'langgraph')",
  "model": "string",
  "provider": "string",
  "trace_id": "string",
  "span_id": "string",
  "idempotency_key": "string",
  "environment": "string",
  "policy_version": "string",
  "detector_version": "string"
}
```

## Design Philosophy
- **Deterministic:** Avoids passing full, unstructured LLM string outputs to the engine; relies on hashes (`arguments_hash`, `response_hash`) for deterministic loop detection to ensure privacy and low latency.
- **Framework Agnostic:** Designed to be implementable as a callback or listener in LangGraph, AutoGen, CrewAI, etc.
