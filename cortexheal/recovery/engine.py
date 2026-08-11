from cortexheal.models.recovery import RecoveryPlan, RecoveryAction
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.storage.postgres import get_recovery_plan_by_incident, save_recovery_plan, get_run, get_events_for_run, save_audit_event
from cortexheal.recovery.ai_provider import RecoveryAIProvider, MockAIProvider, RealAIProvider
from cortexheal.recovery.policy import PolicyEngine
from cortexheal.recovery.executor import RecoveryExecutor
from cortexheal.learning.pattern import PatternEngine
from cortexheal.learning.ranking import RankingEngine
from cortexheal.learning.ml import RecoveryPredictor
import os

class RecoveryEngine:
    def __init__(self, ai_provider: RecoveryAIProvider = None):
        if ai_provider:
            self.ai_provider = ai_provider
        else:
            if os.environ.get("CORTEXHEAL_AI_API_KEY"):
                self.ai_provider = RealAIProvider()
            else:
                self.ai_provider = MockAIProvider()
        self.policy = PolicyEngine()
        self.executor = RecoveryExecutor()
        self.pattern_engine = PatternEngine()
        self.ranking_engine = RankingEngine()
        self.ml_predictor = RecoveryPredictor()

    def generate_plan(self, incident: Incident) -> RecoveryPlan:
        # Idempotency check: does a plan already exist?
        existing_plan = get_recovery_plan_by_incident(incident.incident_id)
        if existing_plan and existing_plan.status not in ["PLAN_STALE", "REJECTED"]:
            return existing_plan
            
        run = get_run(incident.run_id)
        events = get_events_for_run(incident.run_id)
        
        snapshot_status = run.status if run else "unknown"
        # Get the latest sequence number as a snapshot version indicator
        snapshot_seq = events[-1].sequence_number if events else 0
            
        # Deterministic Diagnosis
        if incident.failure_type == "STUCK_LOOP":
            diagnosis = "Identical execution signature repeated beyond threshold."
            proposed = RecoveryAction(
                run_id=incident.run_id,
                incident_id=incident.incident_id,
                action_type="KEEP_PAUSED",
                reason="Default safety posture for unresolvable stuck loops.",
                risk_level="LOW"
            )
        elif incident.failure_type == "BUDGET_EXCEEDED":
            diagnosis = "Run exceeded configured cost threshold."
            proposed = RecoveryAction(
                run_id=incident.run_id,
                incident_id=incident.incident_id,
                action_type="KEEP_PAUSED",
                reason="Default safety posture for budget overruns.",
                risk_level="LOW"
            )
        else:
            diagnosis = f"Detected failure of type: {incident.failure_type}"
            proposed = RecoveryAction(
                run_id=incident.run_id,
                incident_id=incident.incident_id,
                action_type="KEEP_PAUSED",
                reason="Unknown incident type. Safest action is to remain paused.",
                risk_level="LOW"
            )
            
        # Deterministic Learning and Pattern Matching
        trigger_event = next((e for e in events if e.event_id == incident.trigger_event_id), events[-1] if events else None)
        if trigger_event:
            try:
                # 1. Fingerprint and Pattern
                pattern = self.pattern_engine.get_or_create_pattern(incident, trigger_event)
                # 2. Ranking and Trust
                recommendations = self.ranking_engine.rank_actions(pattern)
                
                if recommendations:
                    best = recommendations[0]
                    # Only override deterministic default if Trust is HIGH and supported
                    if best.trust_level == "HIGH" and best.is_supported:
                        proposed.action_type = best.action_type
                        proposed.reason = f"Historical evidence suggests high trust for {best.action_type} ({best.historical_success_rate*100:.1f}% success over {best.verified_attempts} attempts)."
                        proposed.risk_level = best.risk_level
                        
                # 3. ML Preparation (will return PREPARED/INSUFFICIENT_DATA and safely continue)
                try:
                    ml_prediction = self.ml_predictor.predict_success(incident, proposed.action_type)
                except Exception as ml_err:
                    pass
            except Exception as learning_err:
                pass
            
        # AI Analysis
        ai_analysis_dict = None
        planner_type = "DETERMINISTIC"
        risk_level = proposed.risk_level
        
        if self.policy.should_invoke_ai(incident):
            save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AI_ANALYSIS_REQUESTED", actor_type="SYSTEM", actor_id="recovery_engine", result="SUCCESS", reason="Policy allowed AI analysis"))
            save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AI_ANALYSIS_STARTED", actor_type="SYSTEM", actor_id="recovery_engine", result="SUCCESS", reason="Starting AI analysis"))
            try:
                analysis = self.ai_provider.analyze_incident(incident, run, events)
                ai_analysis_dict = analysis.model_dump()
                planner_type = "AI_ASSISTED"
                risk_level = analysis.risk_level
                diagnosis = analysis.diagnosis
                
                # Use AI's recommended action if it is safe and allowed
                if analysis.recommended_action in ["KEEP_PAUSED", "RESUME"]:
                    proposed.action_type = analysis.recommended_action
                    proposed.reason = analysis.reasoning_summary
                    proposed.risk_level = analysis.risk_level
                    
                save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AI_ANALYSIS_COMPLETED", actor_type="SYSTEM", actor_id="recovery_engine", result="SUCCESS", reason="AI analysis completed successfully"))
            except Exception as e:
                # Graceful degradation: AI failure does not block protection
                save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AI_ANALYSIS_FAILED", actor_type="SYSTEM", actor_id="recovery_engine", result="FAILURE", reason=f"AI Analysis Failed: {e}"))
                save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AI_ANALYSIS_FALLBACK", actor_type="SYSTEM", actor_id="recovery_engine", result="SUCCESS", reason="Falling back to deterministic plan"))
                print(f"AI Analysis Failed: {e}")
                pass
            
        plan = RecoveryPlan(
            incident_id=incident.incident_id,
            run_id=incident.run_id,
            diagnosis=diagnosis,
            proposed_actions=[proposed],
            planner_type=planner_type,
            status="PROPOSED",
            risk_level=risk_level,
            snapshot_run_status=snapshot_status,
            snapshot_sequence_number=snapshot_seq,
            ai_analysis=ai_analysis_dict
        )
        
        save_recovery_plan(plan)
        
        # Evaluate for Safe Automation
        if self.policy.evaluate_automation(plan, incident, run):
            save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AUTOMATION_EXECUTED", actor_type="SYSTEM", actor_id="automation_engine", result="SUCCESS", reason="Plan qualified for safe automation"))
            self.executor.execute_plan(plan, "ADMIN", "automation_engine")
        else:
            save_audit_event(AuditEvent(run_id=incident.run_id, incident_id=incident.incident_id, action="AUTOMATION_REJECTED", actor_type="SYSTEM", actor_id="automation_engine", result="SUCCESS", reason="Plan requires human approval"))
            
        return plan
