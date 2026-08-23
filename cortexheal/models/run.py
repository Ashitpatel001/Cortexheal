from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class AgentRun(BaseModel):
    run_id: str
    agent_id: str
    framework: str
    model: Optional[str] = None
    provider: Optional[str] = None
    status: str = "running" # running, completed, failed
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    total_tokens: int = 0
    total_cost: Optional[float] = None
    failure_reason: Optional[str] = None
    protection_mode: str = "ACTIVE" # ACTIVE, DISABLED, DEGRADED
