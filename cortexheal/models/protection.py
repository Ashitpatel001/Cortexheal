from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    incident_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: Literal[
        'PAUSE_REQUESTED',
        'PAUSED',
        'RESUME_REQUESTED',
        'RESUMED',
        'PAUSE_FAILED',
        'RESUME_FAILED',
        'PLAN_APPROVED',
        'PLAN_REJECTED',
        'PLAN_STALE',
        'ACTION_EXECUTED',
        'AI_ANALYSIS_REQUESTED',
        'AI_ANALYSIS_STARTED',
        'AI_ANALYSIS_COMPLETED',
        'AI_ANALYSIS_FAILED',
        'AI_ANALYSIS_FALLBACK',
        'RECOVERY_VERIFICATION',
        'AUTOMATION_EXECUTED',
        'AUTOMATION_REJECTED',
        'CIRCUIT_BREAKER_TRIPPED'
    ]
    actor_type: Literal['SYSTEM', 'HUMAN'] = 'SYSTEM'
    actor_id: str = 'SYSTEM'
    result: Literal['SUCCESS', 'FAILURE', 'IDEMPOTENT', 'RECOVERY_REPEATED_FAILURE', 'RECOVERY_VERIFIED']
    reason: str
    policy_version: str = "1.0"
