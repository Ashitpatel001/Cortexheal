
from fastapi.testclient import TestClient
from cortexheal.server.api import app, get_current_user, User

client = TestClient(app)

def mock_auth_org_a():
    return User(username="user_a", role="ADMIN", org_id="org_a")

def mock_auth_org_b():
    return User(username="user_b", role="ADMIN", org_id="org_b")

# Retrieve the two runs from the previous seeding via direct DB query
import psycopg2
conn = psycopg2.connect("postgresql://cortexheal:cortexpassword@localhost:5433/cortexheal_db")
cur = conn.cursor()
cur.execute("SELECT run_id FROM runs WHERE org_id = 'org_a' LIMIT 1")
run_a = cur.fetchone()[0]
cur.execute("SELECT run_id FROM runs WHERE org_id = 'org_b' LIMIT 1")
run_b = cur.fetchone()[0]
conn.close()

print(f"Known org_a run_id: {run_a}")
print(f"Known org_b run_id: {run_b}")

print("\n--- Negative Test: org_a API call ---")
app.dependency_overrides[get_current_user] = mock_auth_org_a
resp_a = client.get("/api/fleet").json()
runs_seen_by_a = [r["run_id"] for r in resp_a]
print(f"Runs returned for org_a: {runs_seen_by_a}")
print(f"Is org_b's run ({run_b}) present? {run_b in runs_seen_by_a}")

print("\n--- Negative Test: org_b API call ---")
app.dependency_overrides[get_current_user] = mock_auth_org_b
resp_b = client.get("/api/fleet").json()
runs_seen_by_b = [r["run_id"] for r in resp_b]
print(f"Runs returned for org_b: {runs_seen_by_b}")
print(f"Is org_a's run ({run_a}) present? {run_a in runs_seen_by_b}")

