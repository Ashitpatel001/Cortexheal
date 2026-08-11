from cortexheal.models.recovery import RecoveryPlan
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.storage.postgres import get_audit_events_for_run

class PolicyEngine:
    def __init__(self, max_auto_recoveries_per_run: int = 3):
        self.max_auto_recoveries_per_run = max_auto_recoveries_per_run

    def should_invoke_ai(self, incident: Incident) -> bool:
        """Determines if AI analysis is permitted for this incident type and severity."""
        if incident.failure_type == "STUCK_LOOP":
            if incident.severity in ["CRITICAL", "HIGH"]:
                return True
        elif incident.failure_type == "BUDGET_EXCEEDED":
            if incident.severity == "HIGH":
                return True
        return False

    def evaluate_automation(self, plan: RecoveryPlan, incident: Incident, run: AgentRun) -> bool:
        """Determines if the proposed recovery plan can be safely auto-executed (Level 2 Automation)."""
        if not run:
            return False
            
        if plan.risk_level != "LOW":
            return False
            
        if incident.failure_type not in ["STUCK_LOOP"]: # Only STUCK_LOOP is allowlisted for V1 automation
            return False
            
        if len(plan.proposed_actions) != 1:
            return False
            
        action = plan.proposed_actions[0]
        if action.action_type not in ["RESUME", "KEEP_PAUSED"]: # Only deterministic/reversible actions
            return False
            
        # Circuit Breaker & Budget Check
        audits = get_audit_events_for_run(run.run_id)
        auto_recoveries = [a for a in audits if a.action == "AUTOMATION_EXECUTED"]
        repeated_failures = [a for a in audits if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE"]
        
        if len(auto_recoveries) >= self.max_auto_recoveries_per_run:
            return False # Budget exceeded
            
        if len(repeated_failures) >= 2:
            return False # Circuit breaker tripped
            
        return True

    def evaluate_plan(self, plan: RecoveryPlan, user_role: str) -> bool:
        # Basic constraints
        if user_role not in ["OPERATOR", "ADMIN"]:
            return False
            
        # For V1, we only allow KEEP_PAUSED or RESUME
        for action in plan.proposed_actions:
            if action.action_type not in ["KEEP_PAUSED", "RESUME"]:
                return False
                
        return True
