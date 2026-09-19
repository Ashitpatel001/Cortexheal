
import os
import sys
import time

for i in range(3):
    os.system(f".\\venv\\Scripts\\python.exe examples/manual_unrecoverable_loop.py")
    print(f"Run {i+1} done")
    time.sleep(1)

from cortexheal.learning.trust import TrustEngine
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


