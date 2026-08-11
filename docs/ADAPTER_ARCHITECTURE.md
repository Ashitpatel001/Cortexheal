# CortexHeal Adapter Architecture

## Decoupling Core from Frameworks
CortexHeal was initially designed against `LangGraph` as the reference framework. In Phase 8, the architecture was fully decoupled into:
1. **CortexHeal Core**: The deterministic runtime event stream, the detection engine, the protection storage plane, and the recovery/policy engines.
2. **Framework Adapters**: The integration layer sitting between the AI agent execution framework (LangGraph, AutoGen, etc.) and the CortexHeal Core.

## Core Abstraction Interface

Adapters must subclass `FrameworkAdapter` defined in `cortexheal.adapters.base`:

```python
class FrameworkAdapter(ABC):
    @property
    @abstractmethod
    def framework_name(self) -> str:
        pass
        
    @abstractmethod
    def get_safety_gate(self) -> Any:
        pass
        
    @abstractmethod
    def get_telemetry_callback(self) -> Any:
        pass
```

### 1. Telemetry Normalization
Frameworks represent loops, LLM calls, and tool calls drastically differently. 
- **LangGraph** uses a directed graph traversal callback system.
- **AutoGen** uses a multi-agent publish/subscribe or functional `register_hook` pattern.

The `get_telemetry_callback()` returns a framework-specific object that intercepts those internal mechanics and normalizes them into exactly the `RuntimeEvent` Pydantic models required by CortexHeal.

### 2. The Safety Gate
The `get_safety_gate()` returns a framework-specific hook that CortexHeal can use to pause and resume the AI agent.
- For **LangGraph**, this is a compiled `StateGraph` node utilizing the native `interrupt()` feature.
- For **AutoGen**, this is an agent message hook that throws a controlled `InterruptedError` to forcibly halt the message loop, as AutoGen lacks native checkpoint suspension.

## Best Practices for Custom Adapters
If you are building an adapter for an internal or proprietary orchestration framework:
1. **Do not put AI logic in the adapter**: The adapter should only format JSON/objects. It shouldn't evaluate whether a tool call is safe.
2. **Fail Open**: If the adapter cannot reach CortexHeal telemetry or Postgres, catch the exception and let the AI agent continue running. Only halt the agent if a `pause_requested` flag is explicitly fetched.
3. **Minimize Overhead**: Avoid blocking HTTP calls in the telemetry callback if possible, or batch them. In CortexHeal's default implementation, telemetry uses async ingestion or lightweight Postgres inserts.
