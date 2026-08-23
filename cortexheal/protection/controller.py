import logging
from typing import List
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.storage.postgres import update_run_status, save_audit_event, get_run

logger = logging.getLogger(__name__)

class ProtectionPolicy:
    def __init__(self):
        self.enabled = True
        self.auto_pause_failures = ["STUCK_LOOP", "BUDGET_EXCEEDED"]

RESUMED_RUNS = {}

class ProtectionController:
    def __init__(self, policy: ProtectionPolicy = ProtectionPolicy()):
        self.policy = policy
        
    def handle_incident(self, incident: Incident):
        """
        Policy gate: decides whether to pause the agent based on an incident.
        """
        if not self.policy.enabled:
            return
            
        if incident.failure_type in self.policy.auto_pause_failures:
            logger.info(f"ProtectionController requesting pause for run {incident.run_id} due to {incident.failure_type}")
            self.request_pause(incident.run_id, incident.incident_id, f"Auto-pause for {incident.failure_type}")

    def request_pause(self, run_id: str, incident_id: str, reason: str):
        """
        Idempotent pause request.
        """
        try:
            RESUMED_RUNS.pop(run_id, None)
            run = get_run(run_id)
            if not run:
                return
                
            if run.protection_mode == 'DISABLED':
                logger.warning(f"PROTECTION_DISABLED for run {run_id}. SafetyGate is missing. Cannot pause.")
                return
                
            if run.protection_mode == 'DEGRADED':
                logger.warning(f"PROTECTION_DEGRADED for run {run_id}. Cannot pause safely.")
                return
                
            if run.status in ['completed', 'failed']:
                save_audit_event(AuditEvent(run_id=run_id, incident_id=incident_id, action='PAUSE_FAILED', actor_type='SYSTEM', actor_id='controller', result='FAILURE', reason='Run already completed or failed'))
                return
                
            if run.status in ['pause_requested', 'paused']:
                save_audit_event(AuditEvent(run_id=run_id, incident_id=incident_id, action='PAUSE_REQUESTED', actor_type='SYSTEM', actor_id='controller', result='IDEMPOTENT', reason='Pause already active'))
                return
                
            # Atomic status update
            updated = update_run_status(run_id, 'pause_requested', expected_statuses=['running', 'resume_requested'])
            if updated:
                save_audit_event(AuditEvent(run_id=run_id, incident_id=incident_id, action='PAUSE_REQUESTED', actor_type='SYSTEM', actor_id='controller', result='SUCCESS', reason=reason))
        except Exception as e:
            logger.error(f"PROTECTION_DEGRADED for run {run_id} due to system failure: {e}")
            try:
                # Attempt to mark DB as degraded if connection partially active
                from cortexheal.storage.postgres import update_run_protection_mode
                update_run_protection_mode(run_id, 'DEGRADED')
            except Exception:
                pass

    def resume(self, run_id: str, actor_id: str, reason: str = "Explicit resume requested", incident_id: str = None):
        """
        Explicitly requests a resume. The user must also invoke the agent framework.
        """
        try:
            run = get_run(run_id)
            if not run:
                return
                
            if run.status in ['completed', 'failed']:
                save_audit_event(AuditEvent(run_id=run_id, action='RESUME_FAILED', actor_type='HUMAN', actor_id=actor_id, result='FAILURE', reason='Run already completed or failed'))
                return
                
            if run.status in ['running', 'resume_requested']:
                save_audit_event(AuditEvent(run_id=run_id, action='RESUME_REQUESTED', actor_type='HUMAN', actor_id=actor_id, result='IDEMPOTENT', reason='Run is not paused'))
                return
                
            updated = update_run_status(run_id, 'resume_requested', expected_statuses=['paused', 'pause_requested'])
            if updated:
                RESUMED_RUNS[run_id] = incident_id
                save_audit_event(AuditEvent(run_id=run_id, incident_id=incident_id, action='RESUME_REQUESTED', actor_type='HUMAN', actor_id=actor_id, result='SUCCESS', reason=reason))
        except Exception as e:
            logger.error(f"Failed to resume run {run_id}: {e}")
