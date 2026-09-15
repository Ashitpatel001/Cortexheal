import logging
import threading
import queue
import time
from typing import Dict, Any

from cortexheal.models.events import RuntimeEvent
from cortexheal.models.run import AgentRun
from cortexheal.storage.postgres import (
    save_event, save_run, get_run, get_events_for_run, save_incident,
    get_audit_events_for_run, save_audit_event, get_recovery_plan_by_incident, save_recovery_plan
)
from cortexheal.detection.engine import DetectionEngine
from cortexheal.protection.controller import ProtectionController
from cortexheal.alerting.dispatcher import alert_dispatcher
from cortexheal.telemetry import metrics
from cortexheal.config import settings

logger = logging.getLogger(__name__)

class RuntimeCollector:
    """
    Ingests, validates, and persists RuntimeEvents deterministically.
    Uses a bounded background queue to provide telemetry backpressure.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self.engine = DetectionEngine()
        self.protection = ProtectionController()
        
        # Bounded Queue
        self.max_queue_size = getattr(settings, 'TELEMETRY_QUEUE_SIZE', max_queue_size)
        metrics.queue_capacity.set(self.max_queue_size)
        self._queue = queue.Queue(maxsize=self.max_queue_size)
        
        self._shutdown_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def ingest_event(self, event: RuntimeEvent):
        """
        Receives an event from the SDK. 
        Enqueues it in a non-blocking manner. If full, drops it.
        """
        metrics.events_received_total.inc()
        try:
            self._queue.put_nowait(event)
            metrics.queue_depth.set(self._queue.qsize())
        except queue.Full:
            metrics.events_dropped_total.inc()
            logger.warning(f"[CortexHeal] Telemetry queue full ({self.max_queue_size}). Dropped event {event.event_id}")

    def _process_queue(self):
        while not self._shutdown_event.is_set():
            try:
                event = self._queue.get(timeout=1.0)
                metrics.queue_depth.set(self._queue.qsize())
                start_time = time.time()
                try:
                    self._sync_process_event(event)
                except Exception as sync_err:
                    logger.error(f"[CortexHeal] Error processing telemetry event {getattr(event, 'event_id', 'unknown')}: {sync_err}")
                finally:
                    latency = time.time() - start_time
                    metrics.ingestion_latency.observe(latency)
                    self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[CortexHeal] Unexpected error in telemetry worker loop: {e}")

    def _sync_process_event(self, event: RuntimeEvent):
        """
        Synchronously saves the event to the DB and evaluates detection logic.
        """
        try:
            # 1. Ensure run exists
            run = get_run(event.run_id)
            if not run:
                run = AgentRun(
                    run_id=event.run_id,
                    agent_id=event.agent_id,
                    framework=event.framework,
                    model=event.model,
                    provider=event.provider,
                    protection_mode="ACTIVE" if event.framework in ["langgraph", "autogen"] else "DISABLED"
                )
                save_run(run)
            
            # 2. Update Run metrics if applicable
            if event.event_type == 'RUN_COMPLETED':
                run.status = 'completed'
                run.end_time = event.timestamp
                
                # Check for RECOVERY_VERIFIED
                from cortexheal.models.protection import AuditEvent
                
                audits = get_audit_events_for_run(run.run_id)
                latest_resume = next((a for a in reversed(audits) if a.action in ["ACTION_EXECUTED", "RESUME_REQUESTED"] and "RESUME" in str(a.action).upper()), None)
                
                if latest_resume:
                    incident_id = latest_resume.incident_id
                    if not incident_id:
                        for a in reversed(audits):
                            if a.incident_id:
                                incident_id = a.incident_id
                                break
                                
                    repeated = [a for a in audits if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_REPEATED_FAILURE" and a.incident_id == incident_id]
                    verified = [a for a in audits if a.action == "RECOVERY_VERIFICATION" and a.result == "RECOVERY_VERIFIED" and a.incident_id == incident_id]
                    
                    if not repeated and not verified:
                        save_audit_event(AuditEvent(
                            run_id=run.run_id, incident_id=incident_id, action="RECOVERY_VERIFICATION",
                            actor_type="SYSTEM", actor_id="collector", result="RECOVERY_VERIFIED", reason="Run completed successfully after resume"
                        ))
                        if incident_id:
                            plan = get_recovery_plan_by_incident(incident_id)
                            if plan:
                                plan.verification_status = "RECOVERY_VERIFIED"
                                save_recovery_plan(plan)
                                from cortexheal.storage.postgres import update_recovery_outcome_verification
                                update_recovery_outcome_verification(incident_id, "VERIFIED_SUCCESS")
            elif event.event_type == 'RUN_FAILED':
                run.status = 'failed'
                run.end_time = event.timestamp
                
            if event.tokens and event.tokens.total > 0:
                run.total_tokens += event.tokens.total
            if event.cost and event.cost > 0:
                run.total_cost = (run.total_cost or 0) + event.cost
                
            # Always save updated run state
            save_run(run)
            
            # 3. Save event
            # Deduplication handled via DB unique constraint on idempotency_key
            saved = save_event(event)
            
            # 4. Evaluate Detection Engine & Protection
            if saved:
                incidents = self.engine.evaluate(event)
                for incident in incidents:
                    save_incident(incident)
                    self.protection.handle_incident(incident)
                    metrics.incidents_created_total.inc()
                    try:
                        alert_dispatcher.dispatch_initial_alert_async(incident)
                    except Exception as alert_err:
                        logger.error(f"[CortexHeal] Failed to dispatch alert for incident {incident.incident_id}: {alert_err}")
                    
            metrics.events_processed_total.inc()
                    
        except Exception as e:
            # Fail-open: CortexHeal DB failures must not bubble back up
            metrics.events_failed_total.inc()
            import traceback
            tb = traceback.format_exc()
            logger.error(f"[CortexHeal] Failed to ingest event {event.event_id} into DB: {e}\n{tb}")

    def shutdown(self, timeout=None):
        self._shutdown_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

# Global instance for the SDK to use
collector = RuntimeCollector()
