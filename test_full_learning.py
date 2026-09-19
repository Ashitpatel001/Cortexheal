
import os
import sys
import uuid
import time
from cortexheal.storage.postgres import get_outcomes_for_pattern, get_recovery_plan_by_incident, get_patterns_by_org

# Delete previous outcomes/patterns to get clean start
# Not actually needed, we will just look at the DB.

print("Running 5 successful recovery loops...")
for i in range(5):
    os.system(f".\\venv\\Scripts\\python.exe examples/demo_stuck_loop_with_recovery.py > NUL 2>&1")
    print(f"Run {i+1} done")
    time.sleep(1)
    
from cortexheal.learning.trust import TrustEngine

# We want to get the latest pattern that has RESUME action.
patterns = get_patterns_by_org("demo_public") # demo default org is demo_public? Wait, the agent_id is support_ticket_router, the run has org_id = default_org
# Actually let us just check all patterns.
from cortexheal.storage.postgres import get_connection
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT pattern_id, fingerprint FROM pattern_records ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        pattern_id = row[0]
        fingerprint = row[1]
        
print(f"\\nPattern: {fingerprint}")
engine = TrustEngine()
evidence = engine.calculate_trust(pattern_id)
print(f"Occurrences: {evidence.occurrences}")
for action, stats in evidence.actions.items():
    print(f"Action: {action} | Attempts: {stats.attempted} | Success: {stats.verified_success} | Fail: {stats.verified_failure} | Rate: {stats.success_rate:.2f} | Trust: {stats.trust_score:.2f} | Risk: {stats.risk_level}")

