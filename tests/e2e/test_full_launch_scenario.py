import pytest
import http.server
import socketserver
import threading
import json
import time
import uuid
import httpx
from fastapi.testclient import TestClient

from cortexheal.server.api import app
from cortexheal.models.events import RuntimeEvent, TokenUsage
from cortexheal.models.run import AgentRun
from cortexheal.runtime.collector import collector
from cortexheal.storage.postgres import (
    init_db, get_connection, get_run, save_run, get_incidents, save_api_key, get_api_key_by_hash
)
from cortexheal.models.auth import ApiKey, hash_key, generate_raw_key

client = TestClient(app)

# Mock Webhook Server
CAPTURED_WEBHOOKS = []

class MockWebhookReceiver(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        CAPTURED_WEBHOOKS.append({
            "path": self.path,
            "payload": parsed
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, format, *args):
        pass

@pytest.fixture(scope="module", autouse=True)
def run_mock_webhook_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 8889), MockWebhookReceiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield
    server.shutdown()
    server.server_close()

def test_full_end_to_end_launch_scenario():
    """
    Comprehensive End-to-End Enterprise Scenario:
    1. Multi-tenant API key authentication.
    2. Register outbound Slack webhook.
    3. Multi-agent execution (Stuck-Loop, Budget-Exceeded, Healthy).
    4. Deterministic circuit-breaking (Auto-pause).
    5. Outbound webhook capture.
    6. Recovery plan generation, human approval, and run resumption.
    7. Compliance audit log export (JSON & CSV).
    """
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE audit_events, recovery_plans, notification_records, webhook_configs, incidents, events, runs, api_keys CASCADE")
            conn.commit()
    collector.engine._emitted.clear()

    # Step 1: Create Organization & Admin API Key
    org_id = "default_org"
    raw_admin_key = generate_raw_key("ADMIN")
    save_api_key(ApiKey(
        key_id=str(uuid.uuid4()),
        key_hash=hash_key(raw_admin_key),
        key_prefix=raw_admin_key[:16] + "...",
        name="Enterprise Launch Admin Key",
        org_id=org_id,
        role="ADMIN"
    ))

    admin_headers = {"X-API-Key": raw_admin_key}

    # Verify whoami
    res_whoami = client.get("/api/whoami", headers=admin_headers)
    assert res_whoami.status_code == 200
    assert res_whoami.json()["role"] == "ADMIN"
    assert res_whoami.json()["org_id"] == org_id

    # Step 2: Register Outbound Alert Webhook
    res_hook = client.post("/api/webhooks", json={
        "url": "http://127.0.0.1:8889/webhook",
        "target_type": "slack",
        "min_severity": "HIGH",
        "escalation_timeout_minutes": 15
    }, headers=admin_headers)
    assert res_hook.status_code == 200
    webhook_id = res_hook.json()["webhook_id"]

    # Step 3: Run Multi-Agent Workload
    run_stuck = f"e2e_stuck_{uuid.uuid4().hex[:6]}"
    run_budget = f"e2e_budget_{uuid.uuid4().hex[:6]}"
    run_healthy = f"e2e_healthy_{uuid.uuid4().hex[:6]}"

    # 3A. Ingest Stuck Loop Agent
    save_run(AgentRun(run_id=run_stuck, agent_id="support_agent", framework="langgraph", status="running", protection_mode="ACTIVE"))
    collector.ingest_event(RuntimeEvent(
        run_id=run_stuck, agent_id="support_agent", framework="langgraph",
        event_type="RUN_STARTED", sequence_number=0, idempotency_key=f"{run_stuck}_0", status="pending"
    ))
    for seq in range(1, 6):
        collector.ingest_event(RuntimeEvent(
            run_id=run_stuck, agent_id="support_agent", framework="langgraph",
            event_type="TOOL_CALL_COMPLETED", sequence_number=seq,
            idempotency_key=f"{run_stuck}_{seq}", status="success",
            tool="query_crm", arguments_hash="hash_same_crm_id", response_hash="hash_same_empty"
        ))

    # 3B. Ingest Budget Overrun Agent
    save_run(AgentRun(run_id=run_budget, agent_id="billing_agent", framework="langgraph", status="running", protection_mode="ACTIVE"))
    collector.ingest_event(RuntimeEvent(
        run_id=run_budget, agent_id="billing_agent", framework="langgraph",
        event_type="RUN_STARTED", sequence_number=0, idempotency_key=f"{run_budget}_0", status="pending"
    ))
    for seq in range(1, 4):
        collector.ingest_event(RuntimeEvent(
            run_id=run_budget, agent_id="billing_agent", framework="langgraph",
            event_type="TOOL_CALL_COMPLETED", sequence_number=seq,
            idempotency_key=f"{run_budget}_{seq}", status="success",
            tool="bulk_llm_inference", cost=0.45,
            tokens=TokenUsage(prompt=12000, completion=4000, total=16000)
        ))

    # 3C. Ingest Healthy Agent
    save_run(AgentRun(run_id=run_healthy, agent_id="healthy_worker", framework="crewai", status="running", protection_mode="ACTIVE"))
    collector.ingest_event(RuntimeEvent(
        run_id=run_healthy, agent_id="healthy_worker", framework="crewai",
        event_type="RUN_STARTED", sequence_number=0, idempotency_key=f"{run_healthy}_0", status="pending"
    ))
    for seq in range(1, 4):
        collector.ingest_event(RuntimeEvent(
            run_id=run_healthy, agent_id="healthy_worker", framework="crewai",
            event_type="TOOL_CALL_COMPLETED", sequence_number=seq,
            idempotency_key=f"{run_healthy}_{seq}", status="success",
            tool=f"step_tool_{seq}", arguments_hash=f"hash_arg_{seq}", response_hash=f"hash_resp_{seq}",
            cost=0.01, tokens=TokenUsage(prompt=200, completion=100, total=300)
        ))

    collector._queue.join()
    time.sleep(0.5)

    # Step 4: Verify Circuit Breaker Trips
    run_stuck_db = get_run(run_stuck)
    run_budget_db = get_run(run_budget)
    run_healthy_db = get_run(run_healthy)

    assert run_stuck_db.status in ["pause_requested", "paused"]
    assert run_budget_db.status in ["pause_requested", "paused"]
    assert run_healthy_db.status == "running"

    # Step 5: Verify Webhook Alerting (async dispatch worker queue)
    delivered = []
    for _ in range(25):
        delivered = [p for p in CAPTURED_WEBHOOKS if run_stuck in json.dumps(p["payload"])]
        if delivered:
            break
        time.sleep(0.1)

    assert len(delivered) >= 1
    slack_blocks = delivered[0]["payload"]["blocks"]
    assert any("STUCK_LOOP" in json.dumps(b) for b in slack_blocks)

    # Step 6: Recovery Plan Generation & Approval
    incidents = [i for i in get_incidents() if i.run_id == run_stuck]
    assert len(incidents) >= 1
    stuck_inc = incidents[0]

    res_plan = client.get(f"/api/incidents/{stuck_inc.incident_id}/plan", headers=admin_headers)
    assert res_plan.status_code == 200
    plan_data = res_plan.json()
    assert plan_data["status"] in ["PROPOSED", "COMPLETED", "APPROVED"]

    if plan_data["status"] == "PROPOSED":
        res_approve = client.post(f"/api/incidents/{stuck_inc.incident_id}/plan/approve", headers=admin_headers)
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "success"

    # Resume Run
    res_resume = client.post(f"/api/runs/{run_stuck}/resume", headers=admin_headers)
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "success"

    # Step 7: Verify Compliance & Audit Exports
    res_export_json = client.get("/api/audit/export?format=json", headers=admin_headers)
    assert res_export_json.status_code == 200
    export_json = res_export_json.json()
    assert export_json["organization_id"] == org_id
    assert export_json["total_records"] >= 2

    res_export_csv = client.get("/api/audit/export?format=csv", headers=admin_headers)
    assert res_export_csv.status_code == 200
    assert "text/csv" in res_export_csv.headers["content-type"]
    assert "incident_id" in res_export_csv.text
    assert "audit_action" in res_export_csv.text
