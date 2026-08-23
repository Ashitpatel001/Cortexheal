from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0

class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    agent_id: str
    parent_run_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: Literal[
        'RUN_STARTED', 
        'LLM_CALL_STARTED', 
        'LLM_CALL_COMPLETED', 
        'TOOL_CALL_STARTED', 
        'TOOL_CALL_COMPLETED', 
        'RUN_COMPLETED', 
        'RUN_FAILED'
    ]
    
    # Tool specific
    tool: Optional[str] = None
    arguments_hash: Optional[str] = None
    response_hash: Optional[str] = None
    
    # Cost tracking
    tokens: Optional[TokenUsage] = None
    cost: Optional[float] = Field(default=None, ge=0.0)
    
    # Performance & State
    latency_ms: Optional[int] = None
    state_hash: Optional[str] = None
    status: Literal['pending', 'success', 'failed']
    
    # Metadata
    sequence_number: int
    framework: str
    model: Optional[str] = None
    provider: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    idempotency_key: str
    environment: str = "production"
    policy_version: str = "1.0"
    detector_version: str = "1.0"
