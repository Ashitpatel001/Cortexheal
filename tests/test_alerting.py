import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from cortexheal.server.api import app
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.models.alerting import WebhookConfig, NotificationRecord
from cortexheal.alerting.dispatcher import alert_dispatcher, AlertDispatcher
from cortexheal.storage.postgres import (
    save_webhook_config, get_webhook_configs_by_org, get_notifications_by_org,
    save_incident, save_run, init_db
)
from cortexheal.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_webhook_crud_and_rbac():
    admin_headers = {"X-API-Key": "dev-admin-key"}
    operator_headers = {"X-API-Key": "dev-operator-key"}
    viewer_headers = {"X-API-Key": "dev-viewer-key"}

    # 1. Non-admin cannot register webhook
    res = client.post("/api/webhooks", json={"url": "https://hooks.slack.com/services/T00/B00/X00"}, headers=viewer_headers)
    assert res.status_code == 403

    res = client.post("/api/webhooks", json={"url": "https://hooks.slack.com/services/T00/B00/X00"}, headers=operator_headers)
    assert res.status_code == 403

    # 2. Admin registers webhook
    res = client.post("/api/webhooks", json={
        "url": "https://hooks.slack.com/services/T00/B00/X00",
        "target_type": "slack",
        "min_severity": "HIGH",
        "escalation_timeout_minutes": 15
    }, headers=admin_headers)
    assert res.status_code == 200
    webhook_data = res.json()
    assert webhook_data["target_type"] == "slack"
    assert webhook_data["url"] == "https://hooks.slack.com/services/T00/B00/X00"
    assert webhook_data["org_id"] == "default_org"
    webhook_id = webhook_data["webhook_id"]

    # 3. Admin lists webhooks
    res = client.get("/api/webhooks", headers=admin_headers)
    assert res.status_code == 200
    assert any(w["webhook_id"] == webhook_id for w in res.json())

    # 4. Admin deletes webhook
    res = client.delete(f"/api/webhooks/{webhook_id}", headers=admin_headers)
    assert res.status_code == 200

    # 5. Delete again returns 404
    res = client.delete(f"/api/webhooks/{webhook_id}", headers=admin_headers)
    assert res.status_code == 404

def test_alert_dispatcher_severity_filtering():
    """Verify that alert_dispatcher only triggers on HIGH or CRITICAL severity."""
    dispatcher = AlertDispatcher()

    # Create dummy mock webhook
    webhook = save_webhook_config(WebhookConfig(
        org_id="test_org",
        target_type="slack",
        url="http://mock-slack.local/webhook",
        min_severity="HIGH"
    ))

    # Test LOW severity -> should NOT fire
    low_incident = Incident(
        incident_id=str(uuid.uuid4()),
        run_id="run_low",
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Minor lag",
        severity="LOW",
        detector="perf_detector",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"observed": 1},
        observed_value=1,
        threshold=4,
        status="OPEN"
    )
    with patch("httpx.Client.post") as mock_post:
        recs = dispatcher.dispatch_initial_alert(low_incident)
        assert len(recs) == 0
        mock_post.assert_not_called()

    # Test MEDIUM severity -> should NOT fire
    med_incident = Incident(
        incident_id=str(uuid.uuid4()),
        run_id="run_med",
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Moderate lag",
        severity="MEDIUM",
        detector="perf_detector",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"observed": 2},
        observed_value=2,
        threshold=4,
        status="OPEN"
    )
    with patch("httpx.Client.post") as mock_post:
        recs = dispatcher.dispatch_initial_alert(med_incident)
        assert len(recs) == 0
        mock_post.assert_not_called()

    # Test HIGH severity -> MUST fire
    high_incident = Incident(
        incident_id=str(uuid.uuid4()),
        run_id="run_high",
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Stuck in repetition loop",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"iterations": 5},
        observed_value=5,
        threshold=4,
        status="OPEN"
    )
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        recs = dispatcher.dispatch_initial_alert(high_incident)
        assert len(recs) >= 1
        assert mock_post.called
        assert recs[0].status == "SUCCESS"
        assert recs[0].notification_type == "INITIAL_ALERT"

def test_slack_block_kit_payload_structure():
    """Verify Slack Block Kit format includes required context, evidence, and deterministic markers."""
    incident = Incident(
        incident_id="inc_12345",
        run_id="run_abcde",
        agent_id="agent_prod",
        failure_type="BUDGET_EXCEEDED",
        description="Total token budget exceeded limit",
        severity="CRITICAL",
        detector="budget_detector",
        detector_version="1.0",
        trigger_event_id="evt_999",
        evidence={"cost": 1.50},
        observed_value=1.50,
        threshold=1.00,
        status="OPEN"
    )

    payload = AlertDispatcher.format_slack_payload(incident, is_escalation=False)
    assert "🚨" in payload["text"]
    assert "BUDGET_EXCEEDED" in payload["text"]
    
    blocks = payload["blocks"]
    assert len(blocks) >= 3
    # Check fields block
    section = next(b for b in blocks if b.get("type") == "section")
    fields = section["fields"]
    fieldTexts = [f["text"] for f in fields]
    assert any("`inc_12345`" in t for t in fieldTexts)
    assert any("`run_abcde`" in t for t in fieldTexts)
    assert any("*CRITICAL*" in t for t in fieldTexts)
    assert any("1.5" in t for t in fieldTexts)

def test_escalation_engine_timing_and_state():
    """Verify escalation fires when unacknowledged window elapses, but not before or when resolved."""
    dispatcher = AlertDispatcher()

    # Save a webhook with 15m escalation timeout
    webhook = save_webhook_config(WebhookConfig(
        webhook_id=str(uuid.uuid4()),
        org_id="default_org",
        target_type="slack",
        url="http://mock-slack.local/escalation",
        escalation_timeout_minutes=15
    ))

    rid_recent = f"run_rec_{uuid.uuid4().hex[:6]}"
    rid_old = f"run_old_{uuid.uuid4().hex[:6]}"
    rid_resolved = f"run_res_{uuid.uuid4().hex[:6]}"

    # Save runs first to satisfy foreign key constraints
    save_run(AgentRun(run_id=rid_recent, agent_id="agent_1", framework="langgraph", status="running"))
    save_run(AgentRun(run_id=rid_old, agent_id="agent_1", framework="langgraph", status="running"))
    save_run(AgentRun(run_id=rid_resolved, agent_id="agent_1", framework="langgraph", status="completed"))

    # Incident 1: Recent incident (created 5 minutes ago) -> should NOT escalate yet
    recent_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    inc_recent = Incident(
        incident_id=str(uuid.uuid4()),
        run_id=rid_recent,
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Recent loop",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"iterations": 5},
        observed_value=5,
        threshold=4,
        triggered_at=recent_ts,
        status="OPEN"
    )
    save_incident(inc_recent)

    # Incident 2: Unacknowledged incident (created 20 minutes ago) -> MUST escalate
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    inc_old = Incident(
        incident_id=str(uuid.uuid4()),
        run_id=rid_old,
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Stale unacknowledged loop",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"iterations": 5},
        observed_value=5,
        threshold=4,
        triggered_at=old_ts,
        status="OPEN"
    )
    save_incident(inc_old)

    # Incident 3: Resolved incident (created 25 minutes ago) -> should NOT escalate
    inc_resolved = Incident(
        incident_id=str(uuid.uuid4()),
        run_id=rid_resolved,
        agent_id="agent_1",
        failure_type="STUCK_LOOP",
        description="Resolved loop",
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        evidence={"iterations": 5},
        observed_value=5,
        threshold=4,
        triggered_at=old_ts,
        status="RESOLVED"
    )
    save_incident(inc_resolved)

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        escalations = dispatcher.check_and_dispatch_escalations()
        escalated_inc_ids = [e.incident_id for e in escalations]

        # inc_old must be escalated
        assert inc_old.incident_id in escalated_inc_ids
        # inc_recent and inc_resolved must NOT be escalated
        assert inc_recent.incident_id not in escalated_inc_ids
        assert inc_resolved.incident_id not in escalated_inc_ids

        # Running again immediately should NOT re-escalate to the same target (idempotent)
        mock_post.reset_mock()
        second_run = dispatcher.check_and_dispatch_escalations()
        assert inc_old.incident_id not in [e.incident_id for e in second_run]

def test_notification_audit_log_endpoint():
    """Verify notification records are auditable via GET /api/notifications."""
    op_headers = {"X-API-Key": "dev-operator-key"}
    res = client.get("/api/notifications", headers=op_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
