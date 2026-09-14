
import requests
import psycopg2
import uuid

conn = psycopg2.connect("postgresql://cortexheal:cortexpassword@localhost:5433/cortexheal_db")
cur = conn.cursor()

# Insert two runs in different orgs
run_a = str(uuid.uuid4())
run_b = str(uuid.uuid4())

cur.execute("""
    INSERT INTO runs (run_id, agent_id, status, framework, protection_mode, org_id) 
    VALUES (%s, %s, %s, %s, %s, %s)
""", (run_a, "support_agent", "running", "langchain", "ACTIVE", "org_a"))

cur.execute("""
    INSERT INTO runs (run_id, agent_id, status, framework, protection_mode, org_id) 
    VALUES (%s, %s, %s, %s, %s, %s)
""", (run_b, "support_agent", "running", "langchain", "ACTIVE", "org_b"))

conn.commit()
conn.close()
print("Seeded two runs in DB with org_a and org_b")

