import logging
from typing import List, Dict, Optional

from cortexheal.models.events import RuntimeEvent
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.storage.postgres import save_incident, get_audit_events_for_run, save_audit_event, get_run
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
                        if not hasattr(self, '_last_db_check'):
                            self._last_db_check = {}
                            
                        import time
                        now = time.time()
                        if now - self._last_db_check.get(dedup_key, 0) < 1.0:
                            continue
                        self._last_db_check[dedup_key] = now
                    
                    # Recovery Verification Check
                    # Check if there is a resume AFTER our last emitted incident
                    is_new_failure_after_resume = False
                    audits = get_audit_events_for_run(event.run_id)
                    latest_resume = next((a for a in reversed(audits) if a.action in ["ACTION_EXECUTED", "RESUME_REQUESTED"] and "RESUME" in str(a.action).upper()), None)
                    
                    if latest_resume and dedup_key in self._emitted:
                        # Find the event sequence of the resume (if possible), or just check timestamps
                        # Since we don't have resume sequence easily, we can check if the resume timestamp 
                        # is newer than the last incident we emitted? We don't store timestamp in _emitted right now.
                        # Actually, if we just check if latest_resume is newer than the incident...
                        pass
                        
                    # Better logic: if there is a resume, we should allow a NEW incident to be emitted if it's a repeated failure!
                    # To keep it simple: if dedup_key in _emitted, we ONLY process if we need to emit RECOVERY_REPEATED_FAILURE
                    if dedup_key in self._emitted:
                        if latest_resume:
                            incident_id = latest_resume.incident_id
                            if not incident_id:
                                for a in reversed(audits):
                                    if a.incident_id:
                                        incident_id = a.incident_id
                                        break
                            
                            repeated = [a for a in audits if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE" and a.incident_id == incident_id]
                            if not repeated:
                                save_audit_event(AuditEvent(
                                    run_id=event.run_id, incident_id=incident_id, action="RECOVERY_VERIFICATION",
                                    actor_type="SYSTEM", actor_id="detection_engine", result="RECOVERY_REPEATED_FAILURE", reason=f"Repeated failure detected after resume"
                                ))
                                if incident_id:
                                    from cortexheal.storage.postgres import get_recovery_plan_by_incident, save_recovery_plan
                                    plan = get_recovery_plan_by_incident(incident_id)
                                    if plan:
                                        plan.verification_status = "RECOVERY_REPEATED_FAILURE"
                                        save_recovery_plan(plan)
                                from cortexheal.protection.controller import ProtectionController
                                ProtectionController().request_pause(event.run_id, incident_id, "Repeated failure safe posture")
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
                    
                    if latest_resume:
                        incident_id = latest_resume.incident_id
                        if not incident_id:
                            for a in reversed(audits):
                                if a.incident_id:
                                    incident_id = a.incident_id
                                    break
                                    
                        save_audit_event(AuditEvent(
                            run_id=event.run_id, incident_id=incident_id, action="RECOVERY_VERIFICATION",
                            actor_type="SYSTEM", actor_id="detection_engine", result="RECOVERY_REPEATED_FAILURE", reason=f"New incident {incident.incident_id} detected after resume"
                        ))
            except Exception as e:
                logger.error(f"Detector {detector.name} failed: {e}")
                
        return incidents
