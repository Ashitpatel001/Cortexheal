import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import httpx
import uuid

from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.models.alerting import WebhookConfig, NotificationRecord
from cortexheal.models.protection import AuditEvent
from cortexheal.storage.postgres import (
    get_active_webhook_configs_by_org,
    save_notification_record,
    get_notifications_for_incident,
    get_incidents,
    get_run,
    save_audit_event
)

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Dedicated background thread pool for outbound alerts and webhook dispatches
# Isolates external network I/O from the real-time telemetry ingestion and detection path
_alert_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="cortexheal-alert-dispatcher")

class AlertDispatcher:
    """
    Handles outbound alerting and escalation dispatch to external notification channels
    (Slack, Webhooks, PagerDuty, Opsgenie) for HIGH and CRITICAL safety incidents.
    """

    def dispatch_initial_alert_async(self, incident: Incident) -> None:
        """
        Asynchronously dispatches initial alerts on an isolated worker thread pool.
        Guarantees that network latency, DNS resolution, and webhook timeouts
        never block the real-time telemetry ingestion loop or safety decision path.
        """
        if incident.severity not in ["HIGH", "CRITICAL"]:
            return
        _alert_executor.submit(self.dispatch_initial_alert, incident)

    @staticmethod
    def format_slack_payload(incident: Incident, is_escalation: bool = False, run: Optional[AgentRun] = None) -> Dict[str, Any]:
        """Formats an incident into a rich Slack Block Kit message."""
        severity_emoji = "🚨" if incident.severity == "CRITICAL" else "⚠️"
        escalation_badge = "🔥 *[ESCALATED - UNACKNOWLEDGED INCIDENT]* " if is_escalation else ""
        header_text = f"{severity_emoji} {escalation_badge}CortexHeal Safety Alert: {incident.failure_type}"

        fields = [
            {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident.incident_id}`"},
            {"type": "mrkdwn", "text": f"*Run ID:*\n`{incident.run_id}`"},
            {"type": "mrkdwn", "text": f"*Agent ID:*\n`{incident.agent_id}`"},
            {"type": "mrkdwn", "text": f"*Severity:*\n*{incident.severity}*"},
            {"type": "mrkdwn", "text": f"*Detector:*\n`{incident.detector} v{incident.detector_version}`"},
            {"type": "mrkdwn", "text": f"*Status:*\n`{incident.status}`"}
        ]

        if incident.observed_value is not None and incident.threshold is not None:
            fields.append({"type": "mrkdwn", "text": f"*Observed Value:*\n{incident.observed_value}"})
            fields.append({"type": "mrkdwn", "text": f"*Threshold:*\n{incident.threshold}"})

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text[:150], "emoji": True}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Description:*\n{incident.description}"},
                "fields": fields
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Deterministic control plane alert triggered at {getattr(incident, 'triggered_at', getattr(incident, 'timestamp', 'now'))} (UTC). Zero LLMs in loop."
                    }
                ]
            }
        ]

        return {
            "text": header_text,
            "blocks": blocks
        }

    @staticmethod
    def format_generic_payload(incident: Incident, is_escalation: bool = False, run: Optional[AgentRun] = None) -> Dict[str, Any]:
        """Formats an incident into a standard JSON webhook payload."""
        return {
            "event": "incident_escalated" if is_escalation else "incident_created",
            "is_escalation": is_escalation,
            "incident": incident.model_dump(),
            "run": run.model_dump() if run else None,
            "dispatched_at": datetime.now(timezone.utc).isoformat()
        }

    def dispatch_alert_to_config(self, config: WebhookConfig, incident: Incident, is_escalation: bool = False) -> NotificationRecord:
        """Sends a notification payload to a specific WebhookConfig target."""
        run = get_run(incident.run_id)
        
        # Build payload based on target type
        if config.target_type == "slack":
            payload = self.format_slack_payload(incident, is_escalation=is_escalation, run=run)
        else:
            payload = self.format_generic_payload(incident, is_escalation=is_escalation, run=run)

        headers = {"Content-Type": "application/json"}
        if config.secret_token:
            headers["Authorization"] = f"Bearer {config.secret_token}"

        status = "FAILED"
        status_code = None
        response_body = None

        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(config.url, json=payload, headers=headers)
                status_code = res.status_code
                response_body = res.text[:500]
                if 200 <= res.status_code < 300:
                    status = "SUCCESS"
                else:
                    status = "FAILED"
        except Exception as e:
            status = "FAILED"
            response_body = str(e)[:500]
            try:
                logger.warning(f"Failed to dispatch alert to {config.url}: {e}")
            except Exception:
                pass

        # Record notification in audit log
        notification = NotificationRecord(
            notification_id=str(uuid.uuid4()),
            org_id=config.org_id,
            incident_id=incident.incident_id,
            run_id=incident.run_id,
            notification_type="ESCALATION" if is_escalation else "INITIAL_ALERT",
            target_url=config.url,
            payload=payload,
            status=status,
            status_code=status_code,
            response_body=response_body,
            sent_at=datetime.now(timezone.utc)
        )
        save_notification_record(notification)

        # Record system audit event
        try:
            save_audit_event(AuditEvent(
                run_id=incident.run_id,
                incident_id=incident.incident_id,
                action="NOTIFICATION_DISPATCHED",
                actor_type="SYSTEM",
                actor_id="alert_dispatcher",
                result="SUCCESS" if status == "SUCCESS" else "FAILURE",
                reason=f"Dispatched {'ESCALATION' if is_escalation else 'INITIAL_ALERT'} to {config.target_type} ({config.url})"
            ))
        except Exception as audit_err:
            logger.warning(f"Failed to record audit event for notification: {audit_err}")

        return notification

    def dispatch_initial_alert(self, incident: Incident) -> List[NotificationRecord]:
        """
        Dispatches initial alert on qualifying incident.
        Strict condition: ONLY fires on HIGH or CRITICAL severity.
        """
        if incident.severity not in ["HIGH", "CRITICAL"]:
            logger.debug(f"Skipping alert dispatch for incident {incident.incident_id} with severity {incident.severity}")
            return []

        # Find org webhooks
        # Use default_org if incident does not specify
        org_id = getattr(incident, "org_id", "default_org") or "default_org"
        configs = get_active_webhook_configs_by_org(org_id)
        
        # If no specific org configs, also check default_org configs
        if not configs and org_id != "default_org":
            configs = get_active_webhook_configs_by_org("default_org")

        results = []
        for config in configs:
            # Check min severity setting of webhook
            if config.min_severity == "CRITICAL" and incident.severity != "CRITICAL":
                continue
            record = self.dispatch_alert_to_config(config, incident, is_escalation=False)
            results.append(record)

        return results

    def check_and_dispatch_escalations(self) -> List[NotificationRecord]:
        """
        Evaluates unacknowledged incidents and dispatches escalation alerts
        if unacknowledged window has elapsed.
        """
        now = datetime.now(timezone.utc)
        open_incidents = [inc for inc in get_incidents() if inc.status == "OPEN" and inc.severity in ["HIGH", "CRITICAL"]]
        
        escalated_records = []

        for incident in open_incidents:
            org_id = getattr(incident, "org_id", "default_org") or "default_org"
            configs = get_active_webhook_configs_by_org(org_id)
            if not configs and org_id != "default_org":
                configs = get_active_webhook_configs_by_org("default_org")

            if not configs:
                continue

            # Parse incident timestamp
            raw_ts = getattr(incident, "triggered_at", None) or getattr(incident, "timestamp", None)
            if raw_ts:
                try:
                    inc_time = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                except Exception:
                    inc_time = now
            else:
                inc_time = now

            existing_notifications = get_notifications_for_incident(incident.incident_id)
            escalated_urls = {n.target_url for n in existing_notifications if n.notification_type == "ESCALATION"}

            for config in configs:
                if config.url in escalated_urls:
                    continue  # Already escalated to this target
                
                timeout_delta = timedelta(minutes=config.escalation_timeout_minutes)
                if now - inc_time >= timeout_delta:
                    # Fire escalation
                    logger.warning(f"Escalating unacknowledged incident {incident.incident_id} after {config.escalation_timeout_minutes}m to {config.url}")
                    rec = self.dispatch_alert_to_config(config, incident, is_escalation=True)
                    escalated_records.append(rec)

        return escalated_records

# Global dispatcher instance
alert_dispatcher = AlertDispatcher()
