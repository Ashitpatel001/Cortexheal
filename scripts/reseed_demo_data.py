"""
CortexHeal Master Demo Data Reseeder
-----------------------------------
Populates the PostgreSQL database with realistic, high-fidelity enterprise agent runs,
safety incidents, recovery plans, audit event verification records, API keys, and webhooks.
"""

import uuid
import time
from datetime import datetime, timezone, timedelta

from cortexheal.storage.postgres import (
    get_connection, init_db, save_run, save_incident, save_audit_event,
    save_recovery_plan, save_api_key, save_webhook_config, save_notification_record
)
from cortexheal.models.run import AgentRun
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.models.recovery import RecoveryPlan, RecoveryAction
from cortexheal.models.auth import ApiKey, hash_key
from cortexheal.models.alerting import WebhookConfig, NotificationRecord

def reseed():
    print("=" * 75)
    print("  RESEEDING CORTEXHEAL ENTERPRISE DEMO DATA")
    print("=" * 75)

    init_db()

    # 1. Clear existing demo data
    print("\n[Step 1] Cleaning existing database tables...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE notification_records, webhook_configs, audit_events, recovery_plans, incidents, events, runs, api_keys CASCADE;")
            conn.commit()
    print("         All tables truncated cleanly.")

    # 2. Seed Multi-Tenant API Keys
    print("\n[Step 2] Seeding Tenant API Keys...")
    keys = [
        ("ctx_admin_prod_corp_001", "Enterprise Root Admin", "ADMIN", "default_org"),
        ("ctx_operator_sre_team_002", "SRE On-Call Operator", "OPERATOR", "default_org"),
        ("ctx_viewer_security_audit_003", "SOC2 Auditor Key", "VIEWER", "default_org")
    ]
    for raw_k, name, role, org in keys:
        save_api_key(ApiKey(
            key_id=str(uuid.uuid4()),
            key_hash=hash_key(raw_k),
            key_prefix=raw_k[:12] + "...",
            name=name,
            org_id=org,
            role=role,
            created_at=datetime.now(timezone.utc)
        ))
    print(f"         Seeded {len(keys)} API Keys.")

    # 3. Seed Alerting Webhooks
    print("\n[Step 3] Seeding Outbound Alerting Webhook Destinations...")
    webhook = save_webhook_config(WebhookConfig(
        webhook_id=str(uuid.uuid4()),
        org_id="default_org",
        target_type="slack",
        url="https://hooks.slack.com/services/T012345/B012345/SAMPLE_WEBHOOK_URL",
        enabled=True,
        min_severity="HIGH",
        escalation_timeout_minutes=15,
        created_at=datetime.now(timezone.utc)
    ))
    print(f"         Seeded Slack Webhook: {webhook.url}")

    # 4. Seed Realistic Runs, Incidents, Recovery Plans & Audit Events
    print("\n[Step 4] Seeding 12 Realistic Enterprise Agent Scenarios...")

    base_time = datetime.now(timezone.utc) - timedelta(hours=3)

    scenarios = [
        {
            "run_id": "run_prod_support_001",
            "agent_id": "support-ticket-router",
            "framework": "langgraph",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 170,
            "failure": None
        },
        {
            "run_id": "run_sql_analyst_002",
            "agent_id": "sql-analyst-agent",
            "framework": "autogen",
            "model": "claude-3-5-sonnet",
            "provider": "anthropic",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 140,
            "failure": "STUCK_LOOP",
            "recovered": True
        },
        {
            "run_id": "run_doc_summarizer_003",
            "agent_id": "document-summarizer-prod",
            "framework": "langgraph",
            "model": "gpt-4o",
            "provider": "openai",
            "status": "paused",
            "protection_mode": "ACTIVE",
            "offset_min": 110,
            "failure": "BUDGET_EXCEEDED",
            "recovered": False
        },
        {
            "run_id": "run_code_reviewer_004",
            "agent_id": "code-reviewer-bot",
            "framework": "crewai",
            "model": "gemini-1.5-pro",
            "provider": "google",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 90,
            "failure": None
        },
        {
            "run_id": "run_billing_reconcile_005",
            "agent_id": "billing-reconciliation-worker",
            "framework": "langgraph",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "status": "paused",
            "protection_mode": "ACTIVE",
            "offset_min": 60,
            "failure": "STUCK_LOOP",
            "recovered": False
        },
        {
            "run_id": "run_inventory_sync_006",
            "agent_id": "inventory-sync-pipeline",
            "framework": "langgraph",
            "model": "gpt-4o",
            "provider": "openai",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 45,
            "failure": "STUCK_LOOP",
            "recovered": True
        },
        {
            "run_id": "run_security_scanner_007",
            "agent_id": "cve-triage-assistant",
            "framework": "custom",
            "model": "claude-3-5-sonnet",
            "provider": "anthropic",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 30,
            "failure": None
        },
        {
            "run_id": "run_claims_evaluator_008",
            "agent_id": "insurance-claims-agent",
            "framework": "langgraph",
            "model": "gpt-4o",
            "provider": "openai",
            "status": "paused",
            "protection_mode": "ACTIVE",
            "offset_min": 15,
            "failure": "BUDGET_EXCEEDED",
            "recovered": False
        },
        {
            "run_id": "run_lead_enricher_009",
            "agent_id": "crm-lead-enricher",
            "framework": "crewai",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "status": "completed",
            "protection_mode": "ACTIVE",
            "offset_min": 5,
            "failure": None
        }
    ]

    for s in scenarios:
        start_ts = (base_time + timedelta(minutes=s["offset_min"])).isoformat()
        end_ts = (base_time + timedelta(minutes=s["offset_min"] + 5)).isoformat() if s["status"] == "completed" else None

        save_run(AgentRun(
            run_id=s["run_id"],
            agent_id=s["agent_id"],
            framework=s["framework"],
            model=s["model"],
            provider=s["provider"],
            status=s["status"],
            protection_mode=s["protection_mode"],
            start_time=start_ts,
            end_time=end_ts
        ))

        # Initial Run Started Audit Event
        save_audit_event(AuditEvent(
            run_id=s["run_id"],
            timestamp=start_ts,
            action="PAUSED" if s["status"] == "paused" else "RESUMED",
            actor_type="SYSTEM",
            actor_id="runtime_collector",
            result="SUCCESS",
            reason=f"Lifecycle state tracking for {s['agent_id']}"
        ))

        # Handle Failures
        if s["failure"] == "STUCK_LOOP":
            inc_ts = (base_time + timedelta(minutes=s["offset_min"] + 2)).isoformat()
            inc_id = str(uuid.uuid4())
            incident = Incident(
                incident_id=inc_id,
                run_id=s["run_id"],
                agent_id=s["agent_id"],
                failure_type="STUCK_LOOP",
                severity="CRITICAL",
                status="RESOLVED" if s.get("recovered") else "OPEN",
                detector="stuck_loop_detector",
                detector_version="1.0",
                trigger_event_id=str(uuid.uuid4()),
                evidence={
                    "tool": "query_database_table",
                    "repetitions": 4,
                    "arguments_hash": "sha256_e823f9a721",
                    "response_hash": "sha256_empty_row_res"
                },
                observed_value=4,
                threshold=4,
                description="Database query tool called 4 consecutive times with identical parameters.",
                triggered_at=inc_ts
            )
            save_incident(incident)

            # Circuit Breaker Trip Audit Event
            save_audit_event(AuditEvent(
                run_id=s["run_id"],
                incident_id=inc_id,
                timestamp=inc_ts,
                action="CIRCUIT_BREAKER_TRIPPED",
                actor_type="SYSTEM",
                actor_id="safety_gate",
                result="SUCCESS",
                reason="Tripped stuck-loop circuit breaker after 4 identical repetitions."
            ))

            # Recovery Plan
            plan_id = str(uuid.uuid4())
            plan = RecoveryPlan(
                plan_id=plan_id,
                incident_id=inc_id,
                run_id=s["run_id"],
                diagnosis="Repetitive failing query due to stale database primary key index.",
                confidence=0.94,
                proposed_actions=[
                    RecoveryAction(
                        action_id=str(uuid.uuid4()),
                        run_id=s["run_id"],
                        incident_id=inc_id,
                        action_type="MODIFY_CONTEXT",
                        reason="Inject fallback secondary index parameter into agent state.",
                        parameters={"use_secondary_index": True},
                        risk_level="LOW",
                        created_at=inc_ts
                    ),
                    RecoveryAction(
                        action_id=str(uuid.uuid4()),
                        run_id=s["run_id"],
                        incident_id=inc_id,
                        action_type="RESUME",
                        reason="Resume agent execution after state adjustment.",
                        parameters={},
                        risk_level="LOW",
                        created_at=inc_ts
                    )
                ],
                risk_level="LOW",
                created_at=inc_ts,
                planner_type="DETERMINISTIC",
                status="APPROVED" if s.get("recovered") else "PROPOSED",
                verification_status="RECOVERY_VERIFIED" if s.get("recovered") else "RECOVERY_UNVERIFIED"
            )
            save_recovery_plan(plan)

            if s.get("recovered"):
                # Plan approval and resumption audit events
                approve_ts = (base_time + timedelta(minutes=s["offset_min"] + 3)).isoformat()
                save_audit_event(AuditEvent(
                    run_id=s["run_id"],
                    incident_id=inc_id,
                    timestamp=approve_ts,
                    action="PLAN_APPROVED",
                    actor_type="HUMAN",
                    actor_id="operator_alex",
                    result="SUCCESS",
                    reason="Approved secondary index switch."
                ))
                save_audit_event(AuditEvent(
                    run_id=s["run_id"],
                    incident_id=inc_id,
                    timestamp=approve_ts,
                    action="RESUMED",
                    actor_type="HUMAN",
                    actor_id="operator_alex",
                    result="RECOVERY_VERIFIED",
                    reason="Verified successful resumption after index fallback."
                ))

        elif s["failure"] == "BUDGET_EXCEEDED":
            inc_ts = (base_time + timedelta(minutes=s["offset_min"] + 2)).isoformat()
            inc_id = str(uuid.uuid4())
            incident = Incident(
                incident_id=inc_id,
                run_id=s["run_id"],
                agent_id=s["agent_id"],
                failure_type="BUDGET_EXCEEDED",
                severity="HIGH",
                status="OPEN",
                detector="budget_detector",
                detector_version="1.0",
                trigger_event_id=str(uuid.uuid4()),
                evidence={
                    "cumulative_cost": 1.45,
                    "budget_limit": 1.00,
                    "total_tokens": 42000,
                    "tool": "large_context_extraction"
                },
                observed_value=1.45,
                threshold=1.00,
                description="Cumulative run cost ($1.4500) exceeded configured limit ($1.0000).",
                triggered_at=inc_ts
            )
            save_incident(incident)

            # Circuit Breaker Trip Audit Event
            save_audit_event(AuditEvent(
                run_id=s["run_id"],
                incident_id=inc_id,
                timestamp=inc_ts,
                action="CIRCUIT_BREAKER_TRIPPED",
                actor_type="SYSTEM",
                actor_id="safety_gate",
                result="SUCCESS",
                reason="Tripped budget circuit breaker after crossing $1.00 limit."
            ))

            # Dispatched Notification Record
            save_notification_record(NotificationRecord(
                notification_id=str(uuid.uuid4()),
                org_id="default_org",
                incident_id=inc_id,
                run_id=s["run_id"],
                notification_type="INITIAL_ALERT",
                target_url=webhook.url,
                payload={"text": f"🚨 Safety Alert: BUDGET_EXCEEDED for {s['agent_id']}"},
                status="SUCCESS",
                status_code=200,
                response_body="ok",
                sent_at=datetime.fromisoformat(inc_ts)
            ))

    print(f"         Seeded {len(scenarios)} Agent Runs with Incidents, Plans & Audits.")

    print("\n" + "=" * 75)
    print("  DATABASE RESEEDING COMPLETE — HIGH REALISM ENTERPRISE DATASET")
    print("=" * 75)

if __name__ == "__main__":
    reseed()
