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
            
        target_signature = (event.tool, event.arguments_hash, event.response_hash)
        
        # Postgres-backed state: fetch the last N-1 tool call completions for this run
        from cortexheal.storage.postgres import get_connection
        from psycopg2.extras import RealDictCursor
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT tool, arguments_hash, response_hash FROM events "
                    "WHERE run_id = %s AND event_type = %s "
                    "ORDER BY sequence_number DESC LIMIT %s",
                    (event.run_id, 'TOOL_CALL_COMPLETED', self.config.repetition_threshold - 1)
                )
                rows = cur.fetchall()
                
        consecutive_count = 1
        for row in rows:
            if (row["tool"], row["arguments_hash"], row["response_hash"]) == target_signature:
                consecutive_count += 1
            else:
                break
                
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
