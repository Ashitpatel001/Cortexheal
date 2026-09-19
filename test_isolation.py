import uuid
import datetime
from cortexheal.models.incident import Incident
from cortexheal.models.events import RuntimeEvent
from cortexheal.learning.pattern import PatternEngine
from cortexheal.storage.postgres import save_pattern_record, save_recovery_outcome, get_connection
from cortexheal.models.learning import RecoveryOutcome
from cortexheal.server.api import get_patterns_api
from cortexheal.server.api import User

trigger_event_id = str(uuid.uuid4())
failure_type = "STUCK_LOOP"
framework = "langgraph"
agent_id = "support_agent"
tool = "query_customer_crm"
arguments_hash = "hash_crm_param_legacy_id"
response_hash = "hash_crm_empty_rows"

org_a = "org_a_uuid"
run_a = str(uuid.uuid4())
incident_a = Incident(
    incident_id=str(uuid.uuid4()), run_id=run_a, agent_id=agent_id, failure_type=failure_type,
    severity="CRITICAL", detector="stuck_loop", detector_version="1.0",
    observed_value=5, threshold=5, description="test",
    trigger_event_id=trigger_event_id, evidence={"token_cost": 10}, timestamp=datetime.datetime.utcnow().isoformat()
)
event_a = RuntimeEvent(
    event_id=trigger_event_id, run_id=run_a, sequence_number=1, event_type="TOOL_CALL_COMPLETED",
    framework=framework, agent_id=agent_id, timestamp=datetime.datetime.utcnow().isoformat(),
    tool=tool, arguments_hash=arguments_hash, response_hash=response_hash, status="success", idempotency_key=str(uuid.uuid4())
)

org_b = "org_b_uuid"
run_b = str(uuid.uuid4())
incident_b = Incident(
    incident_id=str(uuid.uuid4()), run_id=run_b, agent_id=agent_id, failure_type=failure_type,
    severity="CRITICAL", detector="stuck_loop", detector_version="1.0",
    observed_value=5, threshold=5, description="test",
    trigger_event_id=trigger_event_id, evidence={"token_cost": 10}, timestamp=datetime.datetime.utcnow().isoformat()
)
event_b = RuntimeEvent(
    event_id=trigger_event_id, run_id=run_b, sequence_number=1, event_type="TOOL_CALL_COMPLETED",
    framework=framework, agent_id=agent_id, timestamp=datetime.datetime.utcnow().isoformat(),
    tool=tool, arguments_hash=arguments_hash, response_hash=response_hash, status="success", idempotency_key=str(uuid.uuid4())
)

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO runs (run_id, agent_id, status, start_time, protection_mode, org_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (run_a, agent_id, "completed", datetime.datetime.utcnow(), "ACTIVE", org_a))
        cur.execute("INSERT INTO runs (run_id, agent_id, status, start_time, protection_mode, org_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (run_b, agent_id, "completed", datetime.datetime.utcnow(), "ACTIVE", org_b))
        conn.commit()

pattern_engine = PatternEngine()
pattern_a = pattern_engine.get_or_create_pattern(incident_a, event_a, org_a)
pattern_b = pattern_engine.get_or_create_pattern(incident_b, event_b, org_b)

print(f"Org A Pattern ID: {pattern_a.pattern_id}")
print(f"Org B Pattern ID: {pattern_b.pattern_id}")
print(f"Are Pattern IDs different? {pattern_a.pattern_id != pattern_b.pattern_id}")
print(f"Are Fingerprints identical? {pattern_a.fingerprint == pattern_b.fingerprint}")

for _ in range(3):
    save_recovery_outcome(RecoveryOutcome(
        outcome_id=str(uuid.uuid4()), run_id=run_a, incident_id=incident_a.incident_id,
        pattern_id=pattern_a.pattern_id, action_type="KEEP_PAUSED", human_decision="APPROVED",
        approval_actor="admin", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS",
        timestamp=datetime.datetime.utcnow()
    ))

user_b = User(username="admin_b", role="ADMIN", org_id=org_b)
res = get_patterns_api(user=user_b)
print("\\n--- Query /api/patterns as Org B ---")
for p in res["data"]:
    print(f"Pattern {p['pattern_id']} (Occurrences: {p['occurrences']})")
    if p["actions"]:
        for a in p["actions"]:
            print(f"  Action {a['action']}: {a['success_rate']*100}% Trust over {a['attempted']} attempts")
    else:
        print("  Actions: None (Insufficient Data)")

user_a = User(username="admin_a", role="ADMIN", org_id=org_a)
res_a = get_patterns_api(user=user_a)
print("\\n--- Query /api/patterns as Org A ---")
for p in res_a["data"]:
    print(f"Pattern {p['pattern_id']} (Occurrences: {p['occurrences']})")
    if p["actions"]:
        for a in p["actions"]:
            print(f"  Action {a['action']}: {a['success_rate']*100:.0f}% Trust over {a['attempted']} attempts")
    else:
        print("  Actions: None (Insufficient Data)")
