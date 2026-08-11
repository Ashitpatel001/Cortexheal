from typing import Any, Dict, List, Optional
import uuid
import time
import logging

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from cortexheal.adapters.base import FrameworkAdapter
from cortexheal.models.events import RuntimeEvent
from cortexheal.runtime.collector import collector
from cortexheal.storage.postgres import get_run, update_run_status, save_audit_event, update_run_protection_mode
from cortexheal.models.protection import AuditEvent

logger = logging.getLogger(__name__)

class CortexHealLangGraphCallback(BaseCallbackHandler):
    """
    Normalizes LangChain/LangGraph events into CortexHeal RuntimeEvents.
    """
    def __init__(self, agent_id: str, run_id: Optional[str] = None):
        self.agent_id = agent_id
        self.run_id = run_id
        self.sequence = 0
        self.llm_starts = {}

    def _get_seq(self) -> int:
        self.sequence += 1
        return self.sequence
        
    def _ensure_run_started(self, **kwargs):
        if not self.run_id:
            metadata = kwargs.get("metadata", {})
            self.run_id = metadata.get("thread_id", str(uuid.uuid4()))

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        self._ensure_run_started(**kwargs)
        # Only emit RUN_STARTED for the root graph execution
        if kwargs.get("parent_run_id") is None:
            event = RuntimeEvent(
                run_id=self.run_id, agent_id=self.agent_id, framework="langgraph",
                event_type="RUN_STARTED", sequence_number=self._get_seq(),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                idempotency_key=str(uuid.uuid4()),
                status="success"
            )
            try:
                collector.ingest_event(event)
            except Exception as e:
                logger.warning(f"Telemetry ingest failed: {e}")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        # Only emit RUN_COMPLETED for the root graph execution
        if kwargs.get("parent_run_id") is None:
            run = get_run(self.run_id)
            if run and run.status in ['paused', 'pause_requested']:
                return
                
            event = RuntimeEvent(
                run_id=self.run_id, agent_id=self.agent_id, framework="langgraph",
                event_type="RUN_COMPLETED", sequence_number=self._get_seq(),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                idempotency_key=str(uuid.uuid4()),
                status="success"
            )
            try:
                collector.ingest_event(event)
            except Exception:
                pass

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> Any:
        # Only emit RUN_FAILED for the root graph execution
        if kwargs.get("parent_run_id") is None:
            # We don't want GraphInterrupt to be treated as a failure if it's our own pause
            if type(error).__name__ not in ('NodeInterrupt', 'GraphInterrupt'):
                event = RuntimeEvent(
                    run_id=self.run_id, agent_id=self.agent_id, framework="langgraph",
                    event_type="RUN_FAILED", sequence_number=self._get_seq(),
                    timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    idempotency_key=str(uuid.uuid4()),
                    status="failed"
                )
                try:
                    collector.ingest_event(event)
                except Exception:
                    pass

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        self._ensure_run_started(**kwargs)
        run_id = kwargs.get("run_id", str(uuid.uuid4()))
        self.llm_starts[run_id] = time.time()
        
        event = RuntimeEvent(
            run_id=self.run_id, agent_id=self.agent_id, framework="langgraph",
            event_type="LLM_CALL_STARTED", sequence_number=self._get_seq(),
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            idempotency_key=str(uuid.uuid4()),
            status="success"
        )
        try:
            collector.ingest_event(event)
        except Exception:
            pass
            
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        run_id = kwargs.get("run_id")
        latency = None
        if run_id in self.llm_starts:
            latency = int((time.time() - self.llm_starts[run_id]) * 1000)
            
        from cortexheal.models.events import TokenUsage
        tokens_obj = None
        if response.llm_output and "token_usage" in response.llm_output:
            tokens_obj = TokenUsage(
                total=response.llm_output["token_usage"].get("total_tokens", 0)
            )
            
        event = RuntimeEvent(
            run_id=self.run_id, agent_id=self.agent_id, framework="langgraph",
            event_type="LLM_CALL_COMPLETED", sequence_number=self._get_seq(),
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            latency_ms=latency, tokens=tokens_obj,
            idempotency_key=str(uuid.uuid4()),
            status="success"
        )
        try:
            collector.ingest_event(event)
        except Exception:
            pass


def cortexheal_safety_gate(state: Any, config: RunnableConfig) -> Any:
    """
    A LangGraph node that enforces protection policies.
    """
    if "configurable" not in config or "thread_id" not in config["configurable"]:
        return state
        
    run_id = config["configurable"]["thread_id"]
    
    try:
        run = get_run(run_id)
        if not run:
            return state
            
        if run.protection_mode != 'ACTIVE':
            update_run_protection_mode(run_id, 'ACTIVE')
            
        if run.status == 'pause_requested':
            update_run_status(run_id, 'paused')
            save_audit_event(AuditEvent(
                run_id=run_id, action='PAUSED', actor_type='SYSTEM', actor_id='safety_gate', 
                result='SUCCESS', reason='Safety gate engaged'
            ))
            logger.warning(f"Run {run_id} formally paused at safety gate.")
            interrupt("Paused by CortexHeal")
            
            # --- EXECUTION RESUMES HERE WHEN GRAPH RE-INVOKED ---
            run = get_run(run_id)
            if run and run.status == 'resume_requested':
                update_run_status(run_id, 'running')
                save_audit_event(AuditEvent(
                    run_id=run_id, action='RESUMED', actor_type='SYSTEM', actor_id='safety_gate', 
                    result='SUCCESS', reason='Graph resumed via safety gate'
                ))
                logger.info(f"Run {run_id} formally resumed.")
    except Exception as e:
        if type(e).__name__ in ('NodeInterrupt', 'GraphInterrupt'):
            raise 
            
        logger.error(f"PROTECTION_DEGRADED: SafetyGate failed: {e}")
        try:
            update_run_protection_mode(run_id, 'DEGRADED')
        except Exception:
            pass
            
    return state


class LangGraphAdapter(FrameworkAdapter):
    """
    Adapter for LangGraph.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
    @property
    def framework_name(self) -> str:
        return "LangGraph"
        
    def get_safety_gate(self) -> Any:
        return cortexheal_safety_gate
        
    def get_telemetry_callback(self) -> Any:
        return CortexHealLangGraphCallback(agent_id=self.agent_id)
