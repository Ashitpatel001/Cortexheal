
import uuid
import datetime
from cortexheal.models.learning import RecoveryOutcome, PatternRecord
from cortexheal.learning.trust import TrustEngine
from cortexheal.storage.postgres import save_recovery_outcome, save_pattern_record

# 1. Create a dummy pattern directly
pattern = PatternRecord(
    framework="langgraph", agent_id="agent_1", failure_type="STUCK_LOOP",
    fingerprint=f"v1-{uuid.uuid4().hex}", fingerprint_version="v1", occurrences=1
)
save_pattern_record(pattern)
print(f"Created Pattern: {pattern.pattern_id}")

# 2. Insert outcomes manually
outcome1 = RecoveryOutcome(
    outcome_id=str(uuid.uuid4()), run_id=str(uuid.uuid4()), incident_id=str(uuid.uuid4()),
    pattern_id=pattern.pattern_id, action_type="RESUME", human_decision="APPROVED",
    approval_actor="admin", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS",
    timestamp=datetime.datetime.utcnow()
)
outcome2 = RecoveryOutcome(
    outcome_id=str(uuid.uuid4()), run_id=str(uuid.uuid4()), incident_id=str(uuid.uuid4()),
    pattern_id=pattern.pattern_id, action_type="RESUME", human_decision="APPROVED",
    approval_actor="admin", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS",
    timestamp=datetime.datetime.utcnow()
)
outcome3 = RecoveryOutcome(
    outcome_id=str(uuid.uuid4()), run_id=str(uuid.uuid4()), incident_id=str(uuid.uuid4()),
    pattern_id=pattern.pattern_id, action_type="RESUME", human_decision="APPROVED",
    approval_actor="admin", execution_result="EXECUTED", verification_result="VERIFIED_FAILURE",
    timestamp=datetime.datetime.utcnow()
)

save_recovery_outcome(outcome1)
save_recovery_outcome(outcome2)
save_recovery_outcome(outcome3)

# 3. Read Trust Score
trust_engine = TrustEngine()
evidence = trust_engine.calculate_trust(pattern.pattern_id)

print(f"\n--- Trust Evidence for {pattern.pattern_id} ---")
print(f"Occurrences: {evidence.occurrences}")
for action, stats in evidence.actions.items():
    print(f"Action: {action}")
    print(f"  Attempted: {stats.attempted}")
    print(f"  Verified Success: {stats.verified_success}")
    print(f"  Verified Failure: {stats.verified_failure}")
    print(f"  Success Rate: {stats.success_rate:.2f}")
    print(f"  Trust Score: {stats.trust_score:.2f}")
    print(f"  Risk Level: {stats.risk_level}")


