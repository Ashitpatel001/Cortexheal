
from fastapi.testclient import TestClient
from cortexheal.server.api import app, get_current_user, User

client = TestClient(app)
app.dependency_overrides[get_current_user] = lambda: User(username="testadmin", role="ADMIN", org_id="org_a")

print("--- Creating Key Live ---")
resp = client.post("/api/keys", json={"name": "Real Test Key", "role": "OPERATOR"})
print(resp.json())

print("\n--- Listing Keys Live ---")
list_resp = client.get("/api/keys")
print(list_resp.json())

