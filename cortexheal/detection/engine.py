import logging
from typing import List, Dict, Optional

from cortexheal.models.events import RuntimeEvent
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.storage.postgres import (
    save_incident, get_audit_events_for_run, save_audit_event, get_run,
    get_recovery_plan_by_incident, save_recovery_plan
)
from cortexheal.detection.base import BaseDetector
from cortexheal.detection.stuck_loop import StuckLoopDetector, Config as SLConfig
from cortexheal.detection.budget import BudgetDetector, BudgetConfig

logger = logging.getLogger(__name__)

class DetectionEngine:
    def __init__(self, sl_config: SLConfig = SLConfig(), budget_config: BudgetConfig = BudgetConfig()):
        self.detectors: List[BaseDetector] = [
            StuckLoopDetector(sl_config),
            BudgetDetector(budget_config)
        ]
        # dict of dedup_key -> last emitted sequence number
        self._emitted: Dict[tuple, int] = {}
        
    def evaluate(self, event: RuntimeEvent) -> List[Incident]:
        """
        Processes a new event through all registered detectors.
        Returns a list of resulting Incidents, automatically deduplicating
        previously emitted incident types for the same run.
        """
        incidents = []
            
        for detector in self.detectors:
            try:
                result = detector.evaluate(event)
                if result and result.matched:
                    dedup_key = (event.run_id, result.failure_type, detector.version)
                    
                    if dedup_key in self._emitted:
                        from cortexheal.protection.controller import RESUMED_RUNS, ProtectionController
                        if event.run_id in RESUMED_RUNS:
                            incident_id = RESUMED_RUNS.get(event.run_id)
                            if not incident_id:
                                audits = get_audit_events_for_run(event.run_id)
                                latest_resume = next((a for a in reversed(audits) if a.action in ["ACTION_EXECUTED", "RESUME_REQUESTED"] and "RESUME" in str(a.action).upper()), None)
                                if latest_resume:
                                    incident_id = latest_resume.incident_id or next((a.incident_id for a in reversed(audits) if a.incident_id), None)
                            
                            if incident_id:
                                audits = get_audit_events_for_run(event.run_id)
                                repeated = [a for a in audits if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE" and a.incident_id == incident_id]
                                if not repeated:
                                    save_audit_event(AuditEvent(
                                        run_id=event.run_id, incident_id=incident_id, action="RECOVERY_VERIFICATION",
                                        actor_type="SYSTEM", actor_id="detection_engine", result="RECOVERY_REPEATED_FAILURE", reason="Repeated failure detected after resume"
                                    ))
                                    plan = get_recovery_plan_by_incident(incident_id)
                                    if plan:
                                        plan.verification_status = "RECOVERY_REPEATED_FAILURE"
                                        save_recovery_plan(plan)
                                        from cortexheal.storage.postgres import update_recovery_outcome_verification
                                        update_recovery_outcome_verification(incident_id, "VERIFIED_FAILURE")
                                    ProtectionController().request_pause(event.run_id, incident_id, "Repeated failure safe posture")
                                    RESUMED_RUNS.pop(event.run_id, None)
                        continue
                        
                    self._emitted[dedup_key] = event.sequence_number
                    logger.info(f"detector_match detector={detector.name} run_id={event.run_id} failure_type={result.failure_type}")
                    
                    incident = Incident(
                        run_id=event.run_id,
                        agent_id=event.agent_id,
                        failure_type=result.failure_type, # type: ignore
                        severity=result.severity, # type: ignore
                        status='OPEN',
                        detector=detector.name,
                        detector_version=detector.version,
                        trigger_event_id=result.trigger_event_id,
                        evidence=result.evidence,
                        observed_value=result.observed_value,
                        threshold=result.threshold,
                        description=result.description
                    )
                    incidents.append(incident)
            except Exception as e:
                logger.error(f"Detector {detector.name} failed: {e}")
                
        return incidents
