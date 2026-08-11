from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

ActionType = Literal["KEEP_PAUSED", "RESUME", "RETRY", "MODIFY_CONTEXT", "ROLLBACK"]
ActionStatus = Literal["PENDING", "EXECUTING", "COMPLETED", "FAILED"]
PlanStatus = Literal["PROPOSED", "APPROVED", "REJECTED", "EXECUTING", "COMPLETED", "FAILED", "EXPIRED", "PLAN_STALE", "VERIFYING", "VERIFIED"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
VerificationStatus = Literal["RECOVERY_UNVERIFIED", "RECOVERY_VERIFIED", "RECOVERY_REPEATED_FAILURE", "RECOVERY_FAILED", "VERIFICATION_TIMEOUT"]

class RecoveryAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    incident_id: str
    action_type: ActionType
    reason: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = "LOW"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ActionStatus = "PENDING"

class RecoveryPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    run_id: str
    diagnosis: str
    confidence: float = 1.0
    proposed_actions: List[RecoveryAction]
    risk_level: RiskLevel = "LOW"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    planner_type: str = "DETERMINISTIC" # DETERMINISTIC, AI_ASSISTED
    status: PlanStatus = "PROPOSED"
    snapshot_run_status: str = "unknown"
    snapshot_sequence_number: int = 0
    ai_analysis: Optional[Dict[str, Any]] = None
    verification_status: Optional[VerificationStatus] = None

class RecoveryAnalysis(BaseModel):
    diagnosis: str
    evidence: str
    confidence: float
    contributing_factors: List[str]
    proposed_actions: List[Dict[str, Any]]
    recommended_action: str
    risk_level: RiskLevel
    reasoning_summary: str
    limitations: str
