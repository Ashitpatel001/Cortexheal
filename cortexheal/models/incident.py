from typing import Optional, Any, Dict, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    agent_id: str
    failure_type: Literal['STUCK_LOOP', 'BUDGET_EXCEEDED']
    severity: Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    status: Literal['OPEN', 'RESOLVED'] = 'OPEN'
    
    detector: str
    detector_version: str
    
    trigger_event_id: str
    triggered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    evidence: Dict[str, Any]
    observed_value: Any
    threshold: Any
    description: str
