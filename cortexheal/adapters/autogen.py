from typing import Any, Dict, Optional, List
import uuid
import time
from cortexheal.adapters.base import FrameworkAdapter
from cortexheal.models.events import RuntimeEvent
from cortexheal.runtime.collector import collector
import logging

logger = logging.getLogger(__name__)

class AutoGenSafetyGate:
    """
    A callable hook for AutoGen's `process_message_before_send` or similar
    that enforces CortexHeal's protection mechanism.
    """
    def __init__(self, run_id: str):
        self.run_id = run_id
        
    def __call__(self, message: Any, sender: Any, recipient: Any, silent: bool) -> Any:
        # In a real implementation, this would check `get_run(self.run_id)`
        # If run.status == 'pause_requested', it would raise a custom Exception
        # to halt AutoGen execution, or return a signal that stops the conversation.
        # AutoGen does not have native graph `interrupt()` like LangGraph, so 
        # throwing an exception or aborting the turn is the primary mechanism.
        from cortexheal.storage.postgres import get_run, update_run_status, save_audit_event, update_run_protection_mode
        from cortexheal.models.protection import AuditEvent
        
        try:
            run = get_run(self.run_id)
            if not run:
                return message
                
            if run.protection_mode != 'ACTIVE':
                update_run_protection_mode(self.run_id, 'ACTIVE')
                
            if run.status == 'pause_requested':
                update_run_status(self.run_id, 'paused')
                save_audit_event(AuditEvent(
                    run_id=self.run_id, action='PAUSED', actor_type='SYSTEM', actor_id='autogen_safety_gate', 
                    result='SUCCESS', reason='Safety gate engaged in AutoGen'
                ))
                # Halting execution via exception for AutoGen
                raise InterruptedError("Paused by CortexHeal")
                
            if run.status == 'resume_requested':
                update_run_status(self.run_id, 'running')
                save_audit_event(AuditEvent(
                    run_id=self.run_id, action='RESUMED', actor_type='SYSTEM', actor_id='autogen_safety_gate', 
                    result='SUCCESS', reason='AutoGen execution resumed'
                ))
        except Exception as e:
            if isinstance(e, InterruptedError):
                raise
            logger.error(f"PROTECTION_DEGRADED: AutoGen SafetyGate failed: {e}")
            
        return message


class CortexHealAutoGenTelemetry:
    """
    Hooks for AutoGen agent events. 
    Can be registered to ConversableAgent hooks (e.g., `register_hook(hookable_method="generate_reply", ...)`).
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.run_id = None
        self.sequence = 0
        self.llm_start_times = {}

    def _get_seq(self) -> int:
        self.sequence += 1
        return self.sequence
        
    def start_run(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())
        event = RuntimeEvent.model_construct(
            run_id=self.run_id, agent_id=self.agent_id, event_type="RUN_STARTED",
            sequence_number=self._get_seq(), timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            idempotency_key=str(uuid.uuid4())
        )
        try:
            collector.ingest_event(event)
        except Exception as e:
            logger.warning(f"Failed to ingest event: {e}")
        return self.run_id
        
    def on_llm_start(self, messages: List[Dict]):
        msg_id = str(uuid.uuid4())
        self.llm_start_times[msg_id] = time.time()
        event = RuntimeEvent.model_construct(
            run_id=self.run_id, agent_id=self.agent_id, event_type="LLM_CALL_STARTED",
            sequence_number=self._get_seq(), timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            idempotency_key=str(uuid.uuid4())
        )
        try:
            collector.ingest_event(event)
        except Exception:
            pass
        return msg_id
        
    def on_llm_end(self, msg_id: str, response: Any, token_usage: Optional[Dict] = None):
        latency = None
        if msg_id in self.llm_start_times:
            latency = int((time.time() - self.llm_start_times[msg_id]) * 1000)
            
        event = RuntimeEvent.model_construct(
            run_id=self.run_id, agent_id=self.agent_id, event_type="LLM_CALL_COMPLETED",
            sequence_number=self._get_seq(), timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            latency_ms=latency, idempotency_key=str(uuid.uuid4())
        )
        try:
            collector.ingest_event(event)
        except Exception:
            pass


class AutoGenAdapter(FrameworkAdapter):
    """
    Adapter for Microsoft AutoGen framework.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.telemetry = CortexHealAutoGenTelemetry(agent_id)
        
    @property
    def framework_name(self) -> str:
        return "AutoGen"
        
    def get_safety_gate(self) -> Any:
        return AutoGenSafetyGate(self.telemetry.run_id)
        
    def get_telemetry_callback(self) -> Any:
        return self.telemetry
