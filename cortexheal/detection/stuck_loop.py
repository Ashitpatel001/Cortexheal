from typing import Optional, List, Dict, Any
from cortexheal.models.events import RuntimeEvent
from cortexheal.detection.base import BaseDetector, DetectionResult

class Config:
    enabled: bool = True
    repetition_threshold: int = 5
    ignored_tools: List[str] = ["poll_status", "heartbeat", "wait_for_completion"]

class StuckLoopDetector(BaseDetector):
    def __init__(self, config: Config = Config()):
        self.config = config
        # State: run_id -> {"signature": tuple, "count": int}
        self._state: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "stuck_loop_detector"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, event: RuntimeEvent) -> Optional[DetectionResult]:
        if not self.config.enabled:
            return None
            
        if event.event_type != 'TOOL_CALL_COMPLETED':
            return None
            
        if not event.tool or event.tool in self.config.ignored_tools:
            return None
            
        run_id = event.run_id
        target_signature = (event.tool, event.arguments_hash, event.response_hash)
        
        # Initialize or update state
        run_state = self._state.get(run_id, {"signature": None, "count": 0})
        
        if run_state["signature"] == target_signature:
            run_state["count"] += 1
        else:
            run_state["signature"] = target_signature
            run_state["count"] = 1
            
        self._state[run_id] = run_state
        consecutive_count = run_state["count"]
                
        if consecutive_count >= self.config.repetition_threshold:
            return DetectionResult(
                matched=True,
                failure_type="STUCK_LOOP",
                severity="CRITICAL",
                evidence={
                    "tool": event.tool,
                    "arguments_hash": event.arguments_hash,
                    "response_hash": event.response_hash,
                    "repetitions": consecutive_count
                },
                observed_value=consecutive_count,
                threshold=self.config.repetition_threshold,
                description=f"Tool call '{event.tool}' repeated {consecutive_count} times with identical arguments and response.",
                trigger_event_id=event.event_id
            )
            
        return None
