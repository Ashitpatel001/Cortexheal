from cortexheal.models.recovery import RecoveryPlan, RecoveryAction
from cortexheal.recovery.policy import PolicyEngine
from cortexheal.storage.postgres import save_recovery_plan, save_recovery_action, save_audit_event, get_run, get_events_for_run, get_incident, save_recovery_outcome
from cortexheal.models.protection import AuditEvent
from cortexheal.protection.controller import ProtectionController
from cortexheal.models.learning import RecoveryOutcome
from cortexheal.learning.pattern import PatternEngine
import datetime
import uuid

class RecoveryExecutor:
    def __init__(self):
        self.policy = PolicyEngine()
        self.protection_controller = ProtectionController()
        
    def execute_plan(self, plan: RecoveryPlan, user_role: str, user_id: str) -> bool:
        if plan.status != "PROPOSED":
            save_audit_event(AuditEvent(
                run_id=plan.run_id, incident_id=plan.incident_id, action="PLAN_REJECTED",
                actor_type="HUMAN", actor_id=user_id, result="FAILURE", reason="Plan not in PROPOSED state"
            ))
            return False
            
        # Re-validate state (Staleness Protection)
        run = get_run(plan.run_id)
        events = get_events_for_run(plan.run_id)
        current_seq = events[-1].sequence_number if events else 0
        if not run or run.status != plan.snapshot_run_status or current_seq != plan.snapshot_sequence_number:
            plan.status = "PLAN_STALE"
            save_recovery_plan(plan)
            save_audit_event(AuditEvent(
                run_id=plan.run_id, incident_id=plan.incident_id, action="PLAN_REJECTED",
                actor_type="SYSTEM", actor_id="recovery_executor", result="FAILURE", reason="Plan is stale"
            ))
            return False
            
        if not self.policy.evaluate_plan(plan, user_role):
            save_audit_event(AuditEvent(
                run_id=plan.run_id, incident_id=plan.incident_id, action="PLAN_REJECTED",
                actor_type="HUMAN", actor_id=user_id, result="FAILURE", reason="Policy denied execution"
            ))
            return False
            
        # Update plan state
        plan.status = "APPROVED"
        save_recovery_plan(plan)
        save_audit_event(AuditEvent(
            run_id=plan.run_id, incident_id=plan.incident_id, action="PLAN_APPROVED",
            actor_type="HUMAN", actor_id=user_id, result="SUCCESS", reason="Plan approved"
        ))
        
        plan.status = "EXECUTING"
        save_recovery_plan(plan)
        
        success_count = 0
        for action in plan.proposed_actions:
            action.status = "EXECUTING"
            save_recovery_action(action)
            
            try:
                if action.action_type == "KEEP_PAUSED":
                    # No-op operation for safety
                    action.status = "COMPLETED"
                    save_recovery_action(action)
                    save_audit_event(AuditEvent(
                        run_id=plan.run_id, incident_id=plan.incident_id, action="ACTION_EXECUTED",
                        actor_type="HUMAN", actor_id=user_id, result="SUCCESS", reason=f"Executed {action.action_type}"
                    ))
                    success_count += 1
                elif action.action_type == "RESUME":
                    # Defer to ProtectionController safely
                    self.protection_controller.resume(plan.run_id, actor_id=user_id, reason=action.reason, incident_id=plan.incident_id)
                    action.status = "COMPLETED"
                    save_recovery_action(action)
                    save_audit_event(AuditEvent(
                        run_id=plan.run_id, incident_id=plan.incident_id, action="ACTION_EXECUTED",
                        actor_type="HUMAN", actor_id=user_id, result="SUCCESS", reason=f"Executed {action.action_type}"
                    ))
                    success_count += 1
                    plan.verification_status = "RECOVERY_UNVERIFIED"
                else:
                    raise ValueError("Unsupported action type")
            except Exception as e:
                action.status = "FAILED"
                save_recovery_action(action)
                save_audit_event(AuditEvent(
                    run_id=plan.run_id, incident_id=plan.incident_id, action="ACTION_EXECUTED",
                    actor_type="HUMAN", actor_id=user_id, result="FAILURE", reason=f"Failed to execute {action.action_type}: {str(e)}"
                ))
                
        if success_count == len(plan.proposed_actions):
            plan.status = "COMPLETED"
        else:
            plan.status = "FAILED"
            
        save_recovery_plan(plan)
        
        # Learning: Save Recovery Outcomes
        try:
            incident = get_incident(plan.incident_id)
            trigger_event = next((e for e in events if e.event_id == incident.trigger_event_id), events[-1] if events else None)
            if incident and trigger_event:
                pattern = PatternEngine().get_or_create_pattern(incident, trigger_event, get_run(plan.run_id).org_id)
                for action in plan.proposed_actions:
                    outcome = RecoveryOutcome(
                        outcome_id=str(uuid.uuid4()),
                        run_id=plan.run_id,
                        incident_id=plan.incident_id,
                        pattern_id=pattern.pattern_id,
                        action_type=action.action_type,
                        ai_recommendation=plan.proposed_actions[0].action_type if plan.planner_type == "AI_ASSISTED" else None,
                        human_decision="APPROVED",
                        approval_actor=user_id,
                        execution_result="EXECUTED" if action.status == "COMPLETED" else "FAILED",
                        verification_result="UNVERIFIED",
                        timestamp=datetime.datetime.utcnow()
                    )
                    save_recovery_outcome(outcome)
        except Exception as e:
            print(f"Outcome save failed: {e}")
            pass
        
        return plan.status == "COMPLETED"
        
    def reject_plan(self, plan: RecoveryPlan, user_role: str, user_id: str) -> bool:
        if plan.status not in ["PROPOSED", "PLAN_STALE"]:
            return False
            
        if user_role not in ["OPERATOR", "ADMIN"]:
            return False
            
        plan.status = "REJECTED"
        save_recovery_plan(plan)
        save_audit_event(AuditEvent(
            run_id=plan.run_id, incident_id=plan.incident_id, action="PLAN_REJECTED",
            actor_type="HUMAN", actor_id=user_id, result="SUCCESS", reason="Plan explicitly rejected by user"
        ))
        
        # Learning
        if plan.proposed_actions:
            try:
                incident = get_incident(plan.incident_id)
                events = get_events_for_run(plan.run_id)
                trigger_event = next((e for e in events if e.event_id == incident.trigger_event_id), events[-1] if events else None)
                if incident and trigger_event:
                    pattern = PatternEngine().get_or_create_pattern(incident, trigger_event, get_run(plan.run_id).org_id)
                    for action in plan.proposed_actions:
                        outcome = RecoveryOutcome(
                            outcome_id=str(uuid.uuid4()),
                            run_id=plan.run_id,
                            incident_id=plan.incident_id,
                            pattern_id=pattern.pattern_id,
                            action_type=action.action_type,
                            ai_recommendation=plan.proposed_actions[0].action_type if plan.planner_type == "AI_ASSISTED" else None,
                            human_decision="REJECTED",
                            approval_actor=user_id,
                            execution_result="FAILED",
                            verification_result="UNVERIFIED",
                            timestamp=datetime.datetime.utcnow()
                        )
                        save_recovery_outcome(outcome)
            except Exception as e:
                pass
                
        return True
