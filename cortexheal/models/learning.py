from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class FailureFingerprint(BaseModel):
    fingerprint_hash: str
    version: str = "1.0"
    framework: str
    agent_id: str
    failure_type: str
    tool_name: Optional[str] = None

class PatternRecord(BaseModel):
    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    framework: str
    agent_id: str
    failure_type: str
    fingerprint: str
    fingerprint_version: str
    occurrences: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_promotion_candidate: bool = False

class RecoveryOutcome(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    incident_id: str
    pattern_id: str
    action_type: str
    ai_recommendation: Optional[str] = None
    human_decision: Optional[str] = None
    approval_actor: Optional[str] = None
    execution_result: str # 'EXECUTED', 'FAILED'
    verification_result: str # 'VERIFIED_SUCCESS', 'VERIFIED_FAILURE', 'UNVERIFIED'
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ActionStats(BaseModel):
    attempted: int = 0
    verified_success: int = 0
    verified_failure: int = 0
    success_rate: float = 0.0
    trust_score: float = 0.0
    risk_level: str = "UNKNOWN"

class PatternEvidence(BaseModel):
    pattern_id: str
    occurrences: int
    actions: Dict[str, ActionStats]

class RankedRecommendation(BaseModel):
    action_type: str
    historical_success_rate: float
    verified_attempts: int
    risk_level: str
    trust_level: str # 'HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT_EVIDENCE'
    is_supported: bool = True
