import psycopg2
import uuid
import json
from datetime import datetime, timezone

conn = psycopg2.connect("postgresql://cortexheal:cortexpassword@localhost:5433/cortexheal_db")
cur = conn.cursor()

cur.execute("SELECT run_id, agent_id FROM runs LIMIT 1")
row = cur.fetchone()
if not row:
    print("No runs found")
    exit(1)
run_id, agent_id = row

incident_id = str(uuid.uuid4())
cur.execute("""
    INSERT INTO incidents (incident_id, run_id, agent_id, failure_type, severity, status, detector, detector_version, trigger_event_id, triggered_at, evidence, observed_value, threshold, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    incident_id, run_id, agent_id, "STUCK_LOOP", "HIGH", "OPEN", "LoopDetector", "1.0", "evt-123", datetime.now(timezone.utc), json.dumps({"tool": "search"}), '"4"', '"3"', "Demo stuck loop"
))
conn.commit()
print(f"Seeded incident: {incident_id}")

cur.execute("""
    INSERT INTO events (event_id, run_id, agent_id, timestamp, event_type, status, sequence_number, framework, idempotency_key)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    str(uuid.uuid4()), run_id, agent_id, datetime.now(timezone.utc), "RUN_STARTED", "success", 1, "langchain", "idem-1"
))
conn.commit()
conn.close()
